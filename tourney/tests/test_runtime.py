import copy
import io
import json
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from tourney import services as s, operations as ops, portability as port
from tourney.models import *
from tourney.engine import DomainError
from tourney.delivery import deliver_one, maintenance
from tourney.forms import local_instant
from zoneinfo import ZoneInfo

@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"], EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RuntimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", email="owner@example.invalid")
        cls.org = Organization.objects.create(name="Synthetic club", contact_email=cls.owner.email)
        Membership.objects.create(organization=cls.org, user=cls.owner)
        now=timezone.now()
        cls.event=Event.objects.create(organization=cls.org, slug="test-event", title="Synthetic event", status="published", start_at=now-timedelta(hours=1), end_at=now+timedelta(hours=10), registration_open=now-timedelta(days=1), registration_close=now+timedelta(hours=9), venue="Test courts", address="Test park", contact_email=cls.owner.email)
        cls.court=Court.objects.create(event=cls.event,name="Court 1",opens_at=cls.event.start_at,closes_at=cls.event.end_at)
        cls.division=Division.objects.create(event=cls.event,name="Singles",discipline="singles",capacity=4)
        for i in range(4):
            s.register(cls.event.id,cls.owner,cls.registration_data(cls.division,i))
        cls.event.refresh_from_db()

    @staticmethod
    def registration_data(division, i, **extra):
        return {"division":str(division.id), "label":f"Entry {i}", "people":[{"name":f"Player {i}","email":f"player{i}@example.invalid","birth_date":"1990-01-01","accepted":True,"skill":"3.0"}],"assisted":True,"policy_version":1,"send_notices":False,**extra}

    def setUp(self):
        self.client.force_login(self.owner)

    def draw(self):
        self.division.refresh_from_db()
        inputs=s.draw_inputs(self.division)
        s.lock_draw(self.event.id,self.owner,{"division":str(self.division.id),"preview_digest":s.digest(inputs)})
        self.division.refresh_from_db(); self.event.refresh_from_db()
        return s.division_matches(self.division).first()

    def ready_players(self):
        EntryMember.objects.filter(division__event=self.event,active=True).update(checked_in=True,checked_in_at=timezone.now())

    def score(self, match, games=None):
        match.refresh_from_db()
        s.match_action(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"action":"start","court":str(self.court.id)})
        match.refresh_from_db()
        result=s.submit_score(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"games":games or [[11,5]],"outcome":"played"})
        match.refresh_from_db()
        s.confirm_score(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"result":result["id"]})
        match.refresh_from_db()
        return match

    def test_every_get_screen_renders(self):
        match=self.draw(); entry=self.division.entries.first(); person=self.event.participants.first()
        urls=["/","/login/","/dashboard/","/events/new/",reverse("event",args=[self.event.slug]),reverse("event_edit",args=[self.event.slug]),reverse("division_new",args=[self.event.slug]),reverse("schedule",args=[self.event.slug]),reverse("match",args=[self.event.slug,match.id]),reverse("participant_edit",args=[self.event.slug,person.id]),reverse("entry_edit",args=[self.event.slug,entry.id])]
        urls += [reverse(name,args=[self.event.slug]) for name in ("flyer","qr","print_pack","roster_import","archive_import","archive_export","roster_csv","results_csv","my_event","live")]
        urls += [f"/events/{self.event.slug}/desk/?tab={tab}" for tab in ("overview","entries","courts","matches","results","promotion","finance","sanction","activity","staff","reports")]
        for url in urls:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)

    def test_public_privacy_and_private_boundary(self):
        self.event.participants.update(accommodation="SECRET_MEDICAL_NOTE")
        self.client.logout()
        for route in ("event","live","results_csv","flyer"):
            response=self.client.get(reverse(route,args=[self.event.slug]))
            self.assertEqual(response.status_code,200)
            self.assertNotIn(b"SECRET_MEDICAL_NOTE",response.content)
            self.assertNotIn(b"player0@example.invalid",response.content)
            self.assertNotIn(b"1990-01-01",response.content)
        self.event.visibility="private"; self.event.save()
        for route in ("event","live","results_csv","flyer","qr"):
            self.assertEqual(self.client.get(reverse(route,args=[self.event.slug])).status_code,404)

    def test_scorer_assigned_only_and_immediate_revocation(self):
        match=self.draw()
        scorer=get_user_model().objects.create_user("scorer")
        grant=EventGrant.objects.create(event=self.event,user=scorer,role="scorer")
        self.client.force_login(scorer)
        url=reverse("match",args=[self.event.slug,match.id])
        self.assertEqual(self.client.get(url).status_code,403)
        with self.assertRaises(DomainError): s.submit_score(self.event.id,scorer,{"match":str(match.id),"revision":match.revision,"games":[[11,5]]})
        ops.assign_scorer(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"scorer":scorer.id})
        self.assertEqual(self.client.get(url).status_code,200)
        listing=self.client.get(reverse("desk",args=[self.event.slug])+"?tab=matches").content.decode()
        for other in s.division_matches(self.division).exclude(pk=match.pk): self.assertNotIn(other.code,listing)
        grant.delete()
        self.assertEqual(self.client.get(url).status_code,403)

    def test_result_retry_replays_without_duplicate_mutation(self):
        match=self.draw(); self.ready_players()
        s.match_action(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"action":"start","court":str(self.court.id)})
        match.refresh_from_db()
        key=str(uuid.uuid4()); data={"match":str(match.id),"revision":match.revision,"games":[[11,5]],"outcome":"played"}
        first=s.submit_score(self.event.id,self.owner,data,key)
        count=Audit.objects.count()
        self.assertEqual(first,s.submit_score(self.event.id,self.owner,data,key))
        self.assertEqual(Audit.objects.count(),count); self.assertEqual(match.results.count(),1)
        with self.assertRaises(DomainError): s.submit_score(self.event.id,self.owner,{**data,"games":[[11,7]]},key)

    def test_policy_changed_link_does_not_consume(self):
        div=Division.objects.create(event=self.event,name="Guest",discipline="singles")
        payload=self.registration_data(div,9,assisted=False)
        raw,token=s.issue_token("registration","player9@example.invalid",self.event,payload)
        self.client.logout()
        self.assertEqual(self.client.get(f"/link/{raw}/").status_code,200)
        token.refresh_from_db(); self.assertIsNone(token.used_at)
        self.event.policy_version=2; self.event.save()
        response=self.client.post(f"/link/{raw}/",{"accept":"on","policy_version":1})
        self.assertEqual(response.status_code,409)
        token.refresh_from_db(); self.assertIsNone(token.used_at)
        response=self.client.post(f"/link/{raw}/",{"accept":"on","policy_version":2})
        self.assertEqual(response.status_code,302)
        self.assertEqual(div.entries.get().members.get().policy_version,2)
        self.assertEqual(self.client.post(f"/link/{raw}/",{"accept":"on","policy_version":2}).status_code,410)

    def test_waitlist_expiry_maintenance(self):
        s.register(self.event.id,self.owner,self.registration_data(self.division,10))
        first=self.division.entries.get(label="Entry 0")
        s.entry_action(self.event.id,self.owner,{"entry":str(first.id),"action":"withdraw"})
        waiting=self.division.entries.get(label="Entry 10"); self.assertEqual(waiting.status,"offered")
        waiting.offer_expires=timezone.now()-timedelta(seconds=1); waiting.save()
        maintenance(); waiting.refresh_from_db()
        self.assertEqual(waiting.status,"waitlisted"); self.assertTrue(waiting.offer_paused)

    def test_existing_person_at_participant_ceiling(self):
        Participant.objects.bulk_create([Participant(event=self.event,name=f"Unused {i}",email=f"unused{i}@example.invalid",birth_date="1990-01-01") for i in range(124)])
        other=Division.objects.create(event=self.event,name="Second",discipline="singles")
        result=s.register(self.event.id,self.owner,self.registration_data(other,0))
        self.assertEqual(result["status"],"admitted"); self.assertEqual(self.event.participants.count(),128)

    def test_replacement_preserves_old_consent_and_receipts(self):
        entry=self.division.entries.first(); old=entry.members.get()
        Receipt.objects.create(entry=entry,amount_cents=1000,reference="RECEIPT-PRIVATE",actor=self.owner)
        result=ops.edit_entry(self.event.id,self.owner,{"entry":str(entry.id),"action":"replace","member":str(old.id),"name":"Replacement","email":"replacement@example.invalid","birth_date":"1990-01-01","accepted":False,"reason":"Unavailable","policy_version":1})
        self.assertEqual(result["status"],"incomplete")
        old.refresh_from_db(); self.assertFalse(old.active); self.assertIsNotNone(old.accepted_at)
        self.assertEqual(s.balance(entry)["received"],1000)
        self.assertFalse(entry.checked_in)
        with self.assertRaises(DomainError): s.entry_action(self.event.id,None,{"entry":str(entry.id),"participant":str(old.participant_id),"action":"withdraw"})

    def test_court_hold_suspends_active_play_and_blocks_resume(self):
        match=self.draw(); self.ready_players()
        s.match_action(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"action":"start","court":str(self.court.id)})
        ops.court_update(self.event.id,self.owner,{"court":str(self.court.id),"status":"blocked"})
        match.refresh_from_db(); self.assertEqual(match.status,"suspended")
        with self.assertRaises(DomainError): s.match_action(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"action":"resume"})

    def test_actual_rest_blocks_next_match(self):
        match=self.draw(); self.ready_players(); self.score(match)
        other=s.division_matches(self.division).filter(side_a_id__in=[match.side_a_id,match.side_b_id]).exclude(pk=match.id).first()
        if not other: other=s.division_matches(self.division).filter(side_b_id__in=[match.side_a_id,match.side_b_id]).exclude(pk=match.id).first()
        with self.assertRaises(DomainError): s.match_action(self.event.id,self.owner,{"match":str(other.id),"revision":other.revision,"action":"start","court":str(self.court.id)})

    def test_archive_round_trip_relationships_and_no_external_actions(self):
        match=self.draw(); self.ready_players(); self.score(match)
        Receipt.objects.create(entry=match.side_a,amount_cents=500,reference="PRIVATE-REF",actor=self.owner)
        document=port.export_archive(self.event)
        encoded=json.dumps(document)
        self.assertNotIn("/link/",encoded); self.assertNotIn("assigned_scorer",encoded)
        restored=port.import_archive(document,self.org,self.owner)
        self.assertEqual(restored.visibility,"private"); self.assertEqual(restored.status,"draft"); self.assertFalse(restored.external_actions_enabled)
        self.assertEqual(restored.participants.count(),4)
        copied=restored.divisions.get().matches.get(number=match.number)
        self.assertEqual(copied.current_result.games,[[11,5]])
        self.assertEqual(copied.winner.label,match.winner.label)
        self.assertNotEqual(copied.id,match.id)
        before=Outbox.objects.count(); s.notify_entry(copied.side_a,"No delivery","Restored","test")
        self.assertEqual(Outbox.objects.count(),before)

    def test_archive_tamper_and_forged_relation_rejected_atomically(self):
        document=port.export_archive(self.event)
        for mode in ("hash","foreign","field"):
            bad=copy.deepcopy(document)
            if mode=="hash": bad["sha256"]="no"
            elif mode=="foreign": bad["content"]["tables"]["members"][0]["participant"]=str(uuid.uuid4()); bad["sha256"]=s.digest(bad["content"])
            else: bad["content"]["tables"]["participants"][0]["user"]=self.owner.id; bad["sha256"]=s.digest(bad["content"])
            before=Event.objects.count()
            with self.assertRaises(DomainError): port.import_archive(bad,self.org,self.owner)
            self.assertEqual(Event.objects.count(),before)

    def test_outbox_stable_identity_and_interruption(self):
        s.queue_mail(self.event,"test@example.invalid","Hello","Synthetic","unique")
        s.queue_mail(self.event,"test@example.invalid","Hello","Synthetic","unique")
        self.assertTrue(deliver_one())
        row=Outbox.objects.get(key="unique"); self.assertEqual(row.status,"saved_local")
        self.assertFalse(deliver_one())
        row.status="sending"; row.attempted_at=timezone.now()-timedelta(minutes=6); row.save()
        maintenance(); row.refresh_from_db(); self.assertEqual(row.status,"uncertain")
        self.assertFalse(deliver_one())

    def test_delivery_failure_keeps_registration(self):
        s.queue_mail(self.event,"test@example.invalid","Hello","Synthetic","unique")
        with patch("tourney.delivery.EmailMessage.send",side_effect=TimeoutError("secret")): deliver_one()
        row=Outbox.objects.get(key="unique"); self.assertEqual(row.status,"uncertain"); self.assertNotIn("secret",row.error)
        self.assertEqual(self.division.entries.count(),4)

    def test_csv_injection_and_contact_exclusion(self):
        self.division.entries.filter(label="Entry 0").update(label="=HYPERLINK(\"evil\")")
        text=self.client.get(reverse("roster_csv",args=[self.event.slug])).content.decode()
        self.assertIn("'=HYPERLINK",text); self.assertNotIn("@example.invalid",text)
        self.assertEqual(port.csv_text([[" \t=1+1"]]),"' \t=1+1\r\n")

    def test_invalid_inputs_are_4xx(self):
        for url,data in [(reverse("event_command",args=[self.event.slug]),{"action":"hold","revision":"oops"}), (reverse("entry_command",args=[self.event.slug]),{}), (reverse("entry_command",args=[self.event.slug]),{"action":"withdraw","entry":"bad-uuid"}), (reverse("event_command",args=[self.event.slug]),{"action":"hold","operation_key":"bad-key"})]:
            with self.subTest(url=url,data=data): self.assertIn(self.client.post(url,data).status_code,(400,404,409))

    def test_csrf_and_demo_disabled_by_default(self):
        client=Client(enforce_csrf_checks=True); client.force_login(self.owner)
        self.assertEqual(client.post(reverse("event_command",args=[self.event.slug]),{"action":"hold"}).status_code,403)
        self.assertEqual(self.client.post("/demo-login/").status_code,403)
        self.assertEqual(self.client.get("/mailbox/").status_code,404)

    def test_clone_excludes_private_records_and_approval(self):
        self.event.sanction_status="approved_recorded"; self.event.save()
        result=ops.clone_event(self.event.id,self.owner,{})
        clone=Event.objects.get(id=result["id"])
        self.assertEqual(clone.status,"draft"); self.assertEqual(clone.visibility,"private")
        self.assertEqual(clone.divisions.count(),1); self.assertEqual(clone.participants.count(),0)
        self.assertEqual(clone.sanction_status,"not_requested"); self.assertEqual(clone.grants.count(),0)

    def test_csv_preview_and_atomic_import_without_messages(self):
        from tourney.desk_views import CSV_FIELDS
        division=Division.objects.create(event=self.event,name="Import",discipline="singles",capacity=4)
        rows=[CSV_FIELDS,["Import","CSV Entry","CSV Person","csv@example.invalid","1990-01-01","3.0","yes","","","","",""]]
        blob=port.csv_text(rows).encode()
        url=reverse("roster_import",args=[self.event.slug]); before=Outbox.objects.count()
        response=self.client.post(url,{"file":SimpleUploadedFile("roster.csv",blob)})
        self.assertEqual(response.status_code,200); self.assertEqual(division.entries.count(),0)
        preview=self.client.session[f"roster_preview:{self.event.id}"]
        response=self.client.post(url,{"confirm":"1","rows":["2"],"digest":s.digest(preview),"operation_key":str(uuid.uuid4())})
        self.assertEqual(response.status_code,302); self.assertEqual(division.entries.count(),1)
        self.assertEqual(Outbox.objects.count(),before)

    def test_dst_ambiguous_and_nonexistent(self):
        from django.core.exceptions import ValidationError
        for value in ("2026-03-08T02:30","2026-11-01T01:30"):
            with self.assertRaises(ValidationError): local_instant(value,ZoneInfo("America/Chicago"))
        self.assertNotEqual(local_instant("2026-11-01T01:30",ZoneInfo("America/Chicago"),"0"),local_instant("2026-11-01T01:30",ZoneInfo("America/Chicago"),"1"))

    @override_settings(DEBUG=True,DEMO_MODE=True)
    def test_demo_seed_idempotency_and_32_player_pilot(self):
        call_command("seed_demo",stdout=io.StringIO()); call_command("seed_demo",stdout=io.StringIO())
        event=Event.objects.get(slug="community-court-day")
        self.assertEqual(event.participants.count(),32); self.assertEqual(Entry.objects.filter(division__event=event).count(),16)
        self.assertEqual(s.current_matches(event).count(),24)
        owner=get_user_model().objects.get(username="local-demo-organizer")
        for member in EntryMember.objects.filter(division__event=event): s.check_in(event.id,owner,{"member":str(member.id)})
        event.refresh_from_db(); start=timezone.now()+timedelta(minutes=1)
        proposal=s.schedule_proposal(event,start); self.assertEqual(len(proposal["assignments"]),24); self.assertEqual(proposal["unscheduled"],[])
        s.commit_schedule(event.id,owner,proposal)
        for item in sorted(proposal["assignments"],key=lambda a:a["start"]):
            from django.utils.dateparse import parse_datetime
            match=Match.objects.get(pk=item["match"])
            at=parse_datetime(item["start"])
            with patch("django.utils.timezone.now",return_value=at):
                s.match_action(event.id,owner,{"match":str(match.id),"revision":match.revision,"action":"start","court":item["court"]})
                match.refresh_from_db()
                result=s.submit_score(event.id,owner,{"match":str(match.id),"revision":match.revision,"games":[[11,5]],"outcome":"played"})
            match.refresh_from_db()
            with patch("django.utils.timezone.now",return_value=at+timedelta(minutes=20)):
                s.confirm_score(event.id,owner,{"match":str(match.id),"revision":match.revision,"result":result["id"]})
        for division in event.divisions.all(): s.finalize(event.id,owner,{"division":str(division.id)})
        event.refresh_from_db(); self.assertEqual(event.competition,"completed")
        self.assertEqual(s.current_matches(event).filter(status="completed").count(),24)
        self.assertEqual(len(port.public_results(event)["divisions"]),4)

    def test_skill_band_uses_numeric_rating(self):
        division=Division.objects.create(event=self.event,name="Rated",discipline="singles",skill_min="3.0",skill_max="4.0")
        self.assertEqual(s.register(self.event.id,self.owner,self.registration_data(division,99))["status"],"admitted")

    def test_private_entry_recovery_discloses_no_event_details(self):
        self.event.visibility="private"; self.event.title="Hidden event name"; self.event.save()
        self.client.logout()
        url=reverse("my_event",args=[self.event.slug])
        response=self.client.get(url); self.assertEqual(response.status_code,200); self.assertNotIn(b"Hidden event name",response.content)
        response=self.client.post(url,{"email":"player0@example.invalid"}); self.assertEqual(response.status_code,200)
        self.assertTrue(Token.objects.filter(event=self.event,kind="manage").exists())

    def test_staff_change_is_idempotent_and_stale_safe(self):
        self.event.refresh_from_db()
        data={"event_revision":self.event.revision,"action":"invite","email":"staff@example.invalid","role":"scorer"}
        key=str(uuid.uuid4()); ops.staff_update(self.event.id,self.owner,data,key); ops.staff_update(self.event.id,self.owner,data,key)
        self.assertEqual(Token.objects.filter(kind="staff").count(),1)
        with self.assertRaises(DomainError): ops.staff_update(self.event.id,self.owner,data,str(uuid.uuid4()))
        self.assertEqual(Outbox.objects.count(),1)

    def test_delivery_retry_requires_reconciliation_evidence(self):
        row=Outbox.objects.create(event=self.event,key="uncertain",recipient="x@example.invalid",subject="Test",body="Test",status="uncertain",attempts=1)
        with self.assertRaises(DomainError): ops.reconcile_delivery(self.event.id,self.owner,{"message":str(row.id),"action":"retry","reason":"Timeout"})
        ops.reconcile_delivery(self.event.id,self.owner,{"message":str(row.id),"action":"retry","reason":"Local sink checked; no acceptance","not_accepted":True})
        row.refresh_from_db(); self.assertEqual(row.status,"queued")

    def test_proposals_reserve_unscheduled_active_match(self):
        match=self.draw(); self.ready_players()
        s.match_action(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"action":"start","court":str(self.court.id)})
        self.event.refresh_from_db(); now=timezone.now()
        proposal=s.schedule_proposal(self.event,now)
        from django.utils.dateparse import parse_datetime
        self.assertTrue(proposal["assignments"])
        self.assertTrue(all(parse_datetime(a["start"]) >= now+timedelta(minutes=self.event.duration_minutes+self.event.buffer_minutes) for a in proposal["assignments"]))

    def test_partial_results_do_not_certify_unfinished_event(self):
        self.draw()
        ops.partial_results(self.event.id,self.owner,{"division":str(self.division.id),"reason":"Weather ended play"})
        self.division.refresh_from_db(); self.assertEqual(self.division.status,"partial")
        with self.assertRaises(DomainError): s.finalize(self.event.id,self.owner,{"division":str(self.division.id)})

    def test_elimination_correction_propagates_then_blocks_started_descendant(self):
        self.division.format="single_elimination"; self.division.save()
        self.event.rest_minutes=0; self.event.buffer_minutes=0; self.event.save()
        match=self.draw(); self.ready_players(); self.score(match)
        final=s.division_matches(self.division).order_by("-number").first()
        before=final.side_a_id
        match.refresh_from_db()
        s.correct_score(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"games":[[4,11]],"outcome":"played","reason":"Transposed sides"})
        final.refresh_from_db(); self.assertNotEqual(final.side_a_id,before)
        other=s.division_matches(self.division).filter(round=1).exclude(pk=match.pk).first(); self.score(other)
        final.refresh_from_db()
        s.match_action(self.event.id,self.owner,{"match":str(final.id),"revision":final.revision,"action":"start","court":str(self.court.id)})
        match.refresh_from_db()
        with self.assertRaises(DomainError): s.correct_score(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"games":[[11,5]],"outcome":"played","reason":"Late change"})

    def test_pool_correction_after_qualification_is_blocked(self):
        self.division.format="pools"; self.division.qualifiers=1; self.division.save()
        self.event.rest_minutes=0; self.event.buffer_minutes=0; self.event.save()
        match=self.draw(); self.ready_players()
        for pool_match in s.division_matches(self.division): self.score(pool_match)
        s.qualify_pools(self.event.id,self.owner,{"division":str(self.division.id)})
        match.refresh_from_db()
        with self.assertRaises(DomainError) as error: s.correct_score(self.event.id,self.owner,{"match":str(match.id),"revision":match.revision,"games":[[2,11]],"outcome":"played","reason":"Pool changed"})
        self.assertEqual(error.exception.code,"qualification_locked")

    def test_archive_rejects_malformed_nested_intervals(self):
        document=port.export_archive(self.event)
        document["content"]["tables"]["participants"][0]["unavailable"]=[{"start":"not a date","end":"later"}]
        document["sha256"]=s.digest(document["content"])
        with self.assertRaises(DomainError): port.import_archive(document,self.org,self.owner)

    def test_event_creation_and_invalid_settings_revision(self):
        from zoneinfo import ZoneInfo
        zone=ZoneInfo("America/Chicago"); start=timezone.now()+timedelta(days=8)
        fmt=lambda t:t.astimezone(zone).strftime("%Y-%m-%dT%H:%M")
        data={"title":"Created in test","summary":"Synthetic","time_zone":"America/Chicago","start_at":fmt(start),"end_at":fmt(start+timedelta(hours=6)),"registration_open":fmt(timezone.now()),"registration_close":fmt(start-timedelta(hours=1)),"visibility":"private","venue":"Test","address":"Test","contact_email":"owner@example.invalid","participation_policy":"Test policy","refund_policy":"Free","fee_cents":0,"rest_minutes":10,"duration_minutes":25,"buffer_minutes":5,"court_count":2,"template":"doubles"}
        response=self.client.post(reverse("event_create"),data)
        self.assertEqual(response.status_code,302)
        event=Event.objects.get(title="Created in test"); self.assertEqual(event.courts.count(),2)
        response=self.client.post(reverse("event_edit",args=[event.slug]),{**data,"revision":"invalid"})
        self.assertEqual(response.status_code,400)
