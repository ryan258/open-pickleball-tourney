"""Bounded desk operations using the same event transaction/revision protocol."""
from datetime import timedelta, date
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify
from .engine import DomainError
from .models import Event, Court, Division, EntryMember, Participant, Entry, Match, EventGrant, Token
from .services import (command, scoped, eligible, try_admit, occupancy, advance_waitlist, notify_entry,
    audit, issue_token, queue_mail, ensure_revision, current_matches, ACTIVE, integer)
from django.conf import settings


@command("clone_event", "edit", archived_ok=True)
def clone_event(event, actor, data):
    fields = ("title", "summary", "time_zone", "venue", "address", "accessibility", "contact_email", "participation_policy", "refund_policy", "currency", "fee_cents", "rest_minutes", "duration_minutes", "buffer_minutes")
    start = max(event.start_at+timedelta(days=7), timezone.now()+timedelta(days=7))
    new = Event(organization=event.organization, **{f: getattr(event, f) for f in fields}, start_at=start,
        end_at=start+(event.end_at-event.start_at), registration_open=timezone.now(), registration_close=start-timedelta(hours=1), visibility="private")
    new.title = f"{event.title[:130]} (copy)"; new.slug = f"{slugify(new.title)[:100]}-{str(new.id)[:8]}"; new.save()
    for c in event.courts.all():
        Court.objects.create(event=new, name=c.name, opens_at=new.start_at, closes_at=new.end_at)
    fields = ("name", "discipline", "format", "capacity", "target", "best_of", "skill_min", "skill_max", "min_age", "max_age", "pool_count", "qualifiers", "waitlist_enabled")
    for d in event.divisions.all():
        Division.objects.create(event=new, **{f: getattr(d, f) for f in fields})
    audit(new, actor, "cloned_settings", {"source_event": str(event.id)})
    return {"id": str(new.id), "slug": new.slug}


@command("participant_update", "operate")
def participant_update(event, actor, data):
    person = scoped(Participant, event, data["participant"])
    person.accommodation = data["accommodation"]; person.extra_rest_minutes = data["extra_rest_minutes"]
    person.unavailable = data["unavailable"]; person.full_clean(); person.save()
    # Clear only future plans; running play is retained for staff reconciliation.
    ids = person.entry_memberships.filter(active=True).values_list("entry_id", flat=True)
    for match in current_matches(event).filter(status="ready"):
        if match.side_a_id in ids or match.side_b_id in ids:
            match.scheduled_at = None; match.scheduled_end = None; match.court = None; match.pinned = False
            match.revision += 1; match.save()
    return {"id": str(person.id), "status": "updated"}


@command("assign_scorer", "edit")
def assign_scorer(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event"); ensure_revision(match, data)
    scorer = None
    if data.get("scorer"):
        grant = EventGrant.objects.filter(event=event, role="scorer", user_id=integer(data["scorer"]), user__is_active=True).first()
        if not grant:
            raise DomainError("Choose an active scorer from this event.")
        scorer = grant.user
    match.assigned_scorer = scorer; match.revision += 1; match.save()
    return {"match": str(match.id), "revision": match.revision}


@command("court_update", "operate")
def court_update(event, actor, data):
    court = scoped(Court, event, data["court"])
    if data["status"] not in ("available", "blocked", "closed"):
        raise DomainError("Choose a supported court state.")
    court.status = data["status"]; court.notes = data.get("notes", "")[:300]; court.save()
    if court.status != "available":
        for match in current_matches(event).filter(court=court, status__in=["called", "in_progress"]):
            match.status = "ready" if match.status == "called" else "suspended"
            match.called_at = None; match.revision += 1; match.save()
    return {"id": str(court.id), "status": court.status}


@command("edit_entry", "operate")
def edit_entry(event, actor, data):
    entry = scoped(Entry, event, data["entry"], "division__event")
    old_division = entry.division
    if old_division.draw_locked or entry.status not in ("admitted", "waitlisted", "incomplete"):
        raise DomainError("Only active entries without a draw or capacity offer can be changed.")
    if not data.get("reason", "").strip():
        raise DomainError("Record a reason for this entry change.")
    if data["action"] == "transfer":
        dest = scoped(Division, event, data["division"])
        advance_waitlist(dest)
        if dest.id == old_division.id or dest.draw_locked or dest.discipline != old_division.discipline:
            raise DomainError("Choose another unlocked division with the same team size.")
        if occupancy(dest) >= dest.capacity or dest.entries.filter(status="waitlisted", offer_paused=False).exists():
            raise DomainError("Destination has no unreserved space. Its waitlist takes priority.")
        members = entry.members.filter(active=True)
        for m in members:
            eligible(m.participant, dest)
            if EntryMember.objects.filter(division=dest, participant=m.participant, active=True).exists():
                raise DomainError("A participant is already entered in the destination division.")
        entry.division = dest; entry.seed = (dest.entries.aggregate(n=Max("seed"))["n"] or 0)+1
        members.update(division=dest, checked_in=False, checked_in_at=None)
        entry.status = "incomplete"; entry.save(); try_admit(entry)
        advance_waitlist(old_division)
        audit(event, actor, "entry_transferred", {"entry": str(entry.id), "from": str(old_division.id), "to": str(dest.id)})
    elif data["action"] == "replace":
        if integer(data.get("policy_version", -1)) != event.policy_version:
            raise DomainError("Policies changed. Review the current policies before recording acceptance.", "policy_changed", 409)
        member = entry.members.filter(pk=data["member"], active=True).first()
        if not member:
            raise DomainError("Choose a current participant to replace.")
        email = data["email"].lower().strip(); validate_email(email)
        person = event.participants.filter(email=email).first()
        if person:
            if person.birth_date.isoformat() != data["birth_date"]:
                raise DomainError("That email has different identity details. Review the participant record.")
        else:
            if event.participants.count() >= 128:
                raise DomainError("This event has reached the 128-person limit.")
            person = Participant.objects.create(event=event, email=email, name=data["name"], birth_date=date.fromisoformat(data["birth_date"]), skill=data.get("skill") or None)
        eligible(person, old_division)
        if entry.members.filter(participant=person).exists() or EntryMember.objects.filter(division=old_division, participant=person, active=True).exists():
            raise DomainError("This participant already has an entry or membership history here.")
        member.active = False; member.checked_in = False; member.save()
        accepted = data.get("accepted", False)
        EntryMember.objects.create(entry=entry, participant=person, division=old_division, policy_version=event.policy_version,
            accepted_at=timezone.now() if accepted else None, consent_method="assisted_verbal" if accepted else "")
        Token.objects.filter(event=event, kind="partner", payload__entry=str(entry.id), payload__participant=str(member.participant_id), used_at__isnull=True).update(used_at=timezone.now())
        if not accepted:
            raw, token = issue_token("partner", email, event, {"entry": str(entry.id), "participant": str(person.id)}, hours=168)
            queue_mail(event, email, "Accept your replacement entry", f"Review and accept: {settings.SITE_URL}/link/{raw}/", f"replacement:{token.id}")
        try_admit(entry); advance_waitlist(old_division)
        audit(event, actor, "partner_replaced", {"entry": str(entry.id), "old_member": str(member.id), "new_participant": str(person.id)})
    else:
        raise DomainError("Unsupported entry edit.")
    notify_entry(entry, "Entry updated by the desk", "Review your current entry and division. Existing external-payment records remain attached to this entry.", "edited")
    return {"id": str(entry.id), "status": entry.status}


@command("staff_update", "staff", archived_ok=True)
def staff_update(event, actor, data):
    action = data.get("action") or "invite"
    if action == "revoke":
        grant = scoped(EventGrant, event, data.get("grant"))
        Token.objects.filter(event=event, kind="staff", email=grant.user.email, used_at__isnull=True).update(used_at=timezone.now())
        grant.delete()
    elif action == "revoke_invite":
        token = scoped(Token, event, data.get("invite"))
        if token.kind != "staff":
            raise DomainError("Choose a staff invitation.")
        token.used_at = timezone.now(); token.save()
    elif action == "invite":
        if event.status in ("cancelled", "archived"):
            raise DomainError("This event is closed to new staff invitations.")
        email = data.get("email", "").strip().lower(); validate_email(email)
        role = data.get("role")
        if role not in ("director", "desk", "scorer", "promotion", "finance", "viewer"):
            raise DomainError("Choose a supported event role.")
        Token.objects.filter(event=event, kind="staff", email=email, used_at__isnull=True).update(used_at=timezone.now())
        raw, token = issue_token("staff", email, event, {"role": role}, hours=168)
        queue_mail(event, email, f"You're invited · {event.title}", f"Review and accept your {role} invitation: {settings.SITE_URL}/link/{raw}/", f"staff:{token.id}")
    else:
        raise DomainError("Choose a supported staff action.")
    return {"status": action}


@command("reconcile_delivery", "edit", archived_ok=True)
def reconcile_delivery(event, actor, data):
    from .models import Outbox
    row = scoped(Outbox, event, data.get("message"))
    if row.status != "uncertain" or not data.get("reason", "").strip():
        raise DomainError("Choose an uncertain delivery and record reconciliation evidence.")
    if data["action"] == "accepted":
        row.status = "accepted"
    elif data["action"] == "retry" and data.get("not_accepted") and row.attempts < 3:
        row.status = "queued"
    elif data["action"] == "suppress":
        row.status = "suppressed"
    else:
        raise DomainError("A retry needs explicit evidence of no provider acceptance and fewer than three attempts.")
    # Provider evidence is private; the normal audit contains identifiers only.
    row.error = data["reason"][:300]; row.save()
    return {"id": str(row.id), "status": row.status}


@command("partial_results", "finalize")
def partial_results(event, actor, data):
    from .services import division_matches, standings
    division = scoped(Division, event, data["division"])
    if not division.draw_locked or not data.get("reason", "").strip():
        raise DomainError("A published draw and an explanation are required for partial results.")
    if division_matches(division).filter(status__in=ACTIVE).exists():
        raise DomainError("Resolve active matches before publishing partial results.")
    division.status = "partial"; division.final_snapshot = standings(division); division.save()
    audit(event, actor, "partial_snapshot", {"division": str(division.id), "standings": division.final_snapshot})
    return {"id": str(division.id), "status": "partial"}
