import io
from datetime import timedelta
from zoneinfo import ZoneInfo
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from . import services
from .auth import participant_grants, rate_limit
from .engine import DomainError
from .forms import EventForm, DivisionForm, RegistrationForm, ScoreForm, local_instant
from .models import (Organization, Membership, Event, Court, Division, Participant, Entry, EntryMember,
                     Match, Token)
from .permissions import capabilities, require, role_for, require_match


def event_access(request, slug, public=True):
    event = get_object_or_404(Event.objects.select_related("organization"), slug=slug)
    caps = capabilities(request.user, event)
    invited = role_for(request.user, event) or any(v["event"] == str(event.id) for v in participant_grants(request).values())
    if public and ((event.status == "draft" and not caps) or (event.visibility == "private" and not invited)):
        raise Http404("Event not found")
    return event, caps


def home(request):
    events = Event.objects.filter(status__in=["published", "archived", "cancelled"], visibility="public").select_related("organization")
    q = request.GET.get("q", "").strip()
    if q:
        events = events.filter(Q(title__icontains=q) | Q(venue__icontains=q) | Q(address__icontains=q) | Q(organization__name__icontains=q))
    discipline = request.GET.get("discipline", "")
    if discipline in ("singles", "doubles"):
        events = events.filter(divisions__discipline=discipline).distinct()
    when = request.GET.get("when", "upcoming")
    if when == "past":
        events = events.filter(end_at__lt=timezone.now()).order_by("-start_at")
    elif when != "all":
        events = events.filter(end_at__gte=timezone.now())
    if request.GET.get("open"):
        events = events.filter(status="published", registration_open__lte=timezone.now(), registration_close__gt=timezone.now())
    return render(request, "home.html", {"events": events.prefetch_related("divisions", "courts")[:60], "q": q, "when": when, "discipline": discipline})


@login_required
def dashboard(request):
    org_ids = Membership.objects.filter(user=request.user).values_list("organization_id", flat=True)
    events = Event.objects.filter(Q(organization_id__in=org_ids) | Q(grants__user=request.user)).distinct().select_related("organization").prefetch_related("divisions")
    cards = []
    for event in events:
        cards.append({"event": event, "caps": capabilities(request.user, event),
                      "entries": Entry.objects.filter(division__event=event, status="admitted").count(),
                      "matches": services.current_matches(event).filter(status="completed").count()})
    return render(request, "dashboard.html", {"cards": cards, "organizations": Organization.objects.filter(id__in=org_ids)})


@login_required
def event_create(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            organization = Organization.objects.filter(memberships__user=request.user, memberships__role="owner").first()
            if not organization:
                organization = Organization.objects.create(name=request.POST.get("organization_name", "Community organizer").strip()[:120] or "Community organizer", contact_email=request.user.email)
                Membership.objects.create(organization=organization, user=request.user, role="owner")
            event = form.save(commit=False); event.organization = organization
            event.slug = f"{slugify(event.title)[:100] or 'event'}-{str(event.id)[:8]}"; event.save()
            for number in range(1, form.cleaned_data["court_count"]+1):
                Court.objects.create(event=event, name=f"Court {number}", opens_at=event.start_at, closes_at=event.end_at)
            template = request.POST.get("template", "doubles")
            if template != "blank":
                Division.objects.create(event=event, name="Open singles" if template == "singles" else "Community doubles",
                    discipline="singles" if template == "singles" else "doubles",
                    format="single_elimination" if template == "singles" else "round_robin", capacity=8)
            services.audit(event, request.user, "event_created", {})
        messages.success(request, "Your event draft is ready. Review divisions, then publish when you are ready.")
        return redirect("desk", slug=event.slug)
    return render(request, "event_form.html", {"form": form, "creating": True})


@login_required
def event_edit(request, slug):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "edit")
    if event.status in ("archived", "cancelled"):
        raise DomainError("This event is closed to ordinary settings changes.")
    original = Event.objects.get(pk=event.pk)
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked = Event.objects.select_for_update().get(pk=event.pk)
            require(request.user, locked, "edit")
            if locked.status in ("archived", "cancelled"):
                raise DomainError("This event is closed to settings changes.")
            if services.integer(request.POST.get("revision", -1)) != locked.revision:
                raise DomainError("The event changed. Refresh the settings before saving.", "stale", 409)
            if locked.divisions.filter(draw_locked=True).exists():
                protected = ("start_at", "end_at", "time_zone", "rest_minutes", "duration_minutes", "buffer_minutes")
                if any(getattr(original, name) != form.cleaned_data[name] for name in protected):
                    form.add_error(None, "Competition dates and timing are locked with the draw. Use holds and schedule changes during play.")
                    return render(request, "event_form.html", {"form": form, "event": original})
            if original.status == "published" and not form.cleaned_data["notice"].strip():
                form.add_error("notice", "Write the notice participants should receive for this published update.")
                return render(request, "event_form.html", {"form": form, "event": original})
            if form.cleaned_data["court_count"] != original.courts.count():
                form.add_error("court_count", "Use court controls to block existing courts. Court count stays fixed after creation.")
                return render(request, "event_form.html", {"form": form, "event": original})
            updated = form.save(commit=False); updated.revision = locked.revision+1
            if updated.participation_policy != original.participation_policy or updated.refund_policy != original.refund_policy:
                updated.policy_version += 1
            updated.save()
            if not updated.divisions.filter(draw_locked=True).exists():
                updated.courts.update(opens_at=updated.start_at, closes_at=updated.end_at)
            services.audit(updated, request.user, "settings_updated", {"fields": form.changed_data})
            if original.status == "published":
                for entry in Entry.objects.filter(division__event=updated, status__in=["admitted", "waitlisted", "offered", "incomplete"]):
                    services.notify_entry(entry, "Event details updated", form.cleaned_data["notice"], "settings")
        messages.success(request, "Event settings saved.")
        return redirect("desk", slug=event.slug)
    return render(request, "event_form.html", {"form": form, "event": original})


@login_required
def division_edit(request, slug, division_id=None):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "edit")
    division = get_object_or_404(Division, pk=division_id, event=event) if division_id else Division(event=event)
    if division.draw_locked or event.status in ("archived", "cancelled"):
        raise DomainError("Division settings are locked after its draw is published.")
    form = DivisionForm(request.POST or None, instance=division)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked = Event.objects.select_for_update().get(pk=event.pk)
            require(request.user, locked, "edit")
            if locked.status in ("archived", "cancelled"):
                raise DomainError("This event is closed to settings changes.")
            if services.integer(request.POST.get("revision", -1)) != locked.revision:
                raise DomainError("The event changed. Review the division again.", "stale", 409)
            if not division_id and event.divisions.count() >= 8:
                raise DomainError("This installation supports eight divisions per event.")
            if division_id and division.entries.exists():
                old = Division.objects.get(pk=division.id)
                sensitive = ["discipline", "format", "skill_min", "skill_max", "min_age", "max_age"]
                if any(getattr(old, k) != form.cleaned_data[k] for k in sensitive):
                    raise DomainError("Move or withdraw entries before changing their eligibility or competition format.")
                if form.cleaned_data["capacity"] < services.occupancy(division):
                    raise DomainError("Capacity cannot drop below admitted entries and active holds.")
            division = form.save(); locked.revision += 1; locked.save()
            services.audit(locked, request.user, "division_saved", {"division": str(division.id)})
        return redirect("desk", slug=event.slug)
    return render(request, "form_page.html", {"form": form, "title": "Edit division" if division_id else "Add a division", "event": event, "submit": "Save division"})


def public_event(request, slug):
    event, caps = event_access(request, slug)
    divisions = list(event.divisions.all())
    for division in divisions:
        division.rows = services.standings(division)
        division.played = services.division_matches(division).filter(status="completed").count()
        division.total = services.division_matches(division).exclude(status__in=["bye", "void"]).count()
    matches = services.current_matches(event).select_related("division", "side_a", "side_b", "court")
    return render(request, "event.html", {"event": event, "caps": caps, "divisions": divisions,
        "active_matches": matches.filter(status__in=services.ACTIVE), "next_matches": matches.filter(status="ready").order_by("scheduled_at", "number")[:12],
        "courts": event.courts.all(), "tab": request.GET.get("tab", "overview")})


def live(request, slug):
    event, caps = event_access(request, slug)
    matches = services.current_matches(event).select_related("division", "side_a", "side_b", "court", "winner")
    payload = {"revision": event.revision, "updated_at": timezone.now().isoformat(), "status": event.status,
        "hold": event.hold_reason, "matches": [{"id": str(m.id), "code": m.code, "division": m.division.name,
            "a": m.side_a.label if m.side_a else None, "b": m.side_b.label if m.side_b else None,
            "court": m.court.name if m.court else None, "state": m.status,
            "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
            "winner": m.winner.label if m.winner_id else None} for m in matches]}
    return JsonResponse(payload)


def registration(request, slug):
    event, caps = event_access(request, slug)
    division = get_object_or_404(Division, event=event, pk=request.GET.get("division") or request.POST.get("division"))
    assisted = request.GET.get("assisted") == "1" and "operate" in caps
    if not assisted and not event.registration_is_open:
        raise DomainError("Registration is closed. Contact the organizer for help.")
    form = RegistrationForm(request.POST or None, division=division, assisted=assisted)
    if request.method == "POST" and form.is_valid():
        rate_limit(request, "registration", limit=30)
        payload = form.payload()
        if not assisted:
            rate_limit(request, "registration_to", limit=5, identity=payload["people"][0]["email"], per_ip=False)
        payload["policy_version"] = request.POST.get("policy_version")
        try:
            if assisted:
                result = services.register(event.id, request.user, payload, request.POST.get("operation_key"))
                messages.success(request, f"Entry saved: {result['status']}.")
                return redirect(f"/events/{event.slug}/desk/?tab=entries")
            with transaction.atomic():
                payload["assisted"] = False
                raw, token = services.issue_token("registration", payload["people"][0]["email"], event, payload, hours=24)
                services.queue_mail(event, token.email, f"Confirm your registration · {event.title}",
                    f"Review the event policies and confirm your registration:\n{settings.SITE_URL}/link/{raw}/\nA spot is not reserved until your entry is complete.", f"registration:{token.id}")
            return render(request, "registration_sent.html", {"event": event})
        except DomainError as exc:
            form.add_error(None, str(exc))
    return render(request, "registration.html", {"form": form, "division": division, "event": event, "assisted": assisted})


def my_event(request, slug):
    event, caps = event_access(request, slug, public=False)
    if event.status == "draft" and not caps:
        raise Http404("Event not found")  # an unpublished title must not leak through the entry-recovery page
    ids = [pid for pid, grant in participant_grants(request).items() if grant["event"] == str(event.id)]
    people = Participant.objects.filter(event=event, pk__in=ids)
    if not people.exists():
        if request.method == "POST":
            rate_limit(request, "manage_link", limit=10)
            email = request.POST.get("email", "").lower().strip()
            rate_limit(request, "manage_to", limit=5, identity=email, per_ip=False)
            person = event.participants.filter(email=email).first()
            if person:
                with transaction.atomic():
                    raw, token = services.issue_token("manage", person.email, event, {"participant": str(person.id)}, hours=1)
                    services.queue_mail(event, person.email, "Manage your event entry", f"{settings.SITE_URL}/link/{raw}/", f"manage:{token.id}")
            messages.success(request, "If this email has an entry, a manage-entry link has been queued.")
        if event.visibility == "private" and not caps:
            return render(request, "recovery.html")
        return render(request, "my_event.html", {"event": event, "request_link": True})
    entries = Entry.objects.filter(members__participant__in=people, members__active=True).distinct().select_related("division").prefetch_related("members__participant")
    if request.method == "POST":
        entry = get_object_or_404(entries, pk=request.POST.get("entry"))
        person = entry.members.filter(participant__in=people, active=True).first().participant
        services.entry_action(event.id, None, {"entry": str(entry.id), "participant": str(person.id), "action": request.POST.get("action"),
            "reason": request.POST.get("reason", "Participant withdrawal")}, request.POST.get("operation_key"))
        return redirect("my_event", slug=slug)
    for entry in entries:
        entry.money = services.balance(entry)
        entry.next_matches = services.division_matches(entry.division).filter(Q(side_a=entry) | Q(side_b=entry)).exclude(status__in=services.TERMINAL)
    return render(request, "my_event.html", {"event": event, "entries": entries})


@login_required
def desk(request, slug):
    event, caps = event_access(request, slug, public=False)
    if not caps:
        raise DomainError("This event desk is not available to your account.", "forbidden", 403)
    tab = request.GET.get("tab", "overview")
    restrictions = {"overview": "view", "entries": "operate", "courts": "operate", "matches": "score", "results": "view",
                    "promotion": "promote", "finance": "finance", "sanction": "evidence", "activity": "edit", "staff": "staff", "reports": "export"}
    if tab not in restrictions:
        raise Http404()
    if restrictions[tab] not in caps:
        tab = next(k for k, cap in restrictions.items() if cap in caps)
    divisions = list(event.divisions.all())
    matches = services.current_matches(event).select_related("division", "side_a", "side_b", "court").prefetch_related("results")
    if role_for(request.user, event) == "scorer":
        matches = matches.filter(assigned_scorer=request.user)
    context = {"event": event, "caps": caps, "tab": tab, "divisions": divisions, "courts": event.courts.all(),
        "matches": matches, "active_count": matches.filter(status__in=services.ACTIVE).count(),
        "completed_count": matches.filter(status="completed").count(), "match_count": matches.exclude(status__in=["bye", "void"]).count(),
        "entry_count": Entry.objects.filter(division__event=event, status="admitted").count(),
        "waiting_count": Entry.objects.filter(division__event=event, status__in=["waitlisted", "offered", "incomplete"]).count(),
        "checked_count": EntryMember.objects.filter(division__event=event, checked_in=True).count(),
        "role": role_for(request.user, event)}
    if tab in ("entries", "finance"):
        entries = Entry.objects.filter(division__event=event).select_related("division").prefetch_related("members__participant", "receipts")
        q = request.GET.get("q", "").strip()
        if q:
            entries = entries.filter(Q(label__icontains=q) | Q(members__participant__name__icontains=q)).distinct()
        for entry in entries:
            entry.money = services.balance(entry)
        context.update(entries=entries, q=q)
    if tab == "results":
        for division in divisions:
            division.rows = services.standings(division)
    if tab == "activity":
        context["audit_rows"] = event.audit.select_related("actor")[:100]
        context["outbox"] = event.outbox.order_by("-created_at")[:30]
    if tab == "staff":
        context["grants"] = event.grants.select_related("user")
        context["invites"] = Token.objects.filter(event=event, kind="staff", used_at__isnull=True, expires_at__gt=timezone.now())
    if tab == "reports":
        context["packages"] = event.packages.order_by("-created_at")
    return render(request, "desk.html", context)


@login_required
@require_POST
def event_command(request, slug):
    event, caps = event_access(request, slug, public=False)
    action = request.POST.get("action")
    data = {"action": action, "reason": request.POST.get("reason", ""), "message": request.POST.get("message", ""),
            "event_revision": request.POST.get("revision", -1)}
    services.event_action(event.id, request.user, data, request.POST.get("operation_key"))
    messages.success(request, "Event updated.")
    return redirect("desk", slug=slug)


@login_required
@require_POST
def entry_command(request, slug):
    event, caps = event_access(request, slug, public=False)
    action = request.POST.get("action")
    if action == "check_in":
        services.check_in(event.id, request.user, {"event_revision": request.POST.get("revision", -1), "member": request.POST["member"], "checked_in": request.POST.get("checked_in") == "1"}, request.POST.get("operation_key"))
    else:
        services.entry_action(event.id, request.user, {"event_revision": request.POST.get("revision", -1), "entry": request.POST["entry"], "action": action,
            "reason": request.POST.get("reason", "Director-recorded withdrawal")}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=entries")


@login_required
def draw_view(request, slug, division_id):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "edit")
    division = get_object_or_404(Division, pk=division_id, event=event)
    random_seed = request.POST.get("random_seed", "") if request.method == "POST" else request.GET.get("seed", "")
    if request.method == "POST":
        services.lock_draw(event.id, request.user, {"division": str(division.id), "random_seed": random_seed,
            "preview_digest": request.POST["preview_digest"], "event_revision": request.POST["revision"]}, request.POST.get("operation_key"))
        messages.success(request, "Draw locked and published. Check in players, then schedule matches.")
        return redirect(f"/events/{slug}/desk/?tab=matches")
    inputs = services.draw_inputs(division, random_seed)
    entries = {str(e.id): e for e in division.entries.all()}
    n = len(inputs["entries"])
    count = n*(n-1)//2 if division.format == "round_robin" else n-1 if division.format == "single_elimination" else "Depends on pools / final reset"
    return render(request, "draw.html", {"event": event, "division": division, "inputs": inputs, "preview_digest": services.digest(inputs),
        "entries": [entries[i] for i in inputs["entries"]], "match_count": count, "random_seed": random_seed})


@login_required
def schedule_view(request, slug):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "operate")
    if request.method == "POST":
        proposal = request.session.get(f"schedule:{event.id}")
        if not proposal or request.POST.get("digest") != services.digest(proposal):
            raise DomainError("Preview the schedule before committing it.")
        services.commit_schedule(event.id, request.user, proposal, request.POST.get("operation_key"))
        request.session.pop(f"schedule:{event.id}", None)
        messages.success(request, "Schedule committed. Court calls still recheck actual availability.")
        return redirect(f"/events/{slug}/desk/?tab=courts")
    start = max(event.start_at, timezone.now())
    if request.GET.get("start"):
        start = local_instant(request.GET["start"], ZoneInfo(event.time_zone), request.GET.get("fold", ""))
    proposal = services.schedule_proposal(event, start)
    request.session[f"schedule:{event.id}"] = proposal
    match_map = {str(m.id): m for m in services.current_matches(event)}
    court_map = {str(c.id): c for c in event.courts.all()}
    rows = [{**a, "match_object": match_map[a["match"]], "court_object": court_map[a["court"]]} for a in proposal["assignments"]]
    return render(request, "schedule.html", {"event": event, "proposal": proposal, "rows": rows, "digest": services.digest(proposal)})


@login_required
def match_view(request, slug, match_id):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "score")
    match = get_object_or_404(Match.objects.select_related("division", "side_a", "side_b", "court"), pk=match_id, division__event=event)
    require_match(request.user, event, match)
    correction = request.GET.get("correct") == "1"
    if correction:
        require(request.user, event, "correct")
    form = ScoreForm(request.POST if request.method == "POST" and request.POST.get("action") == "score" else None, best_of=services.rules(match.division)["best_of"])
    if request.method == "POST":
        data = {"match": str(match.id), "revision": request.POST.get("revision", -1), "action": request.POST.get("action"),
                "court": request.POST.get("court"), "reason": request.POST.get("reason", "")}
        try:
            if data["action"] == "score":
                if form.is_valid():
                    score = {**data, "games": form.cleaned_data["games"], "outcome": form.cleaned_data["outcome"],
                             "winner": form.cleaned_data["winner"], "reason": form.cleaned_data["reason"], "incomplete_game": form.cleaned_data["incomplete_game"]}
                    fn = services.correct_score if correction else services.submit_score
                    fn(event.id, request.user, score, request.POST.get("operation_key"))
                    return redirect("match", slug=slug, match_id=match.id)
            elif data["action"] == "confirm":
                services.confirm_score(event.id, request.user, {**data, "result": request.POST["result"]}, request.POST.get("operation_key"))
                return redirect("match", slug=slug, match_id=match.id)
            elif data["action"] == "incident":
                services.open_incident(event.id, request.user, data, request.POST.get("operation_key"))
                return redirect("match", slug=slug, match_id=match.id)
            else:
                services.match_action(event.id, request.user, data, request.POST.get("operation_key"))
                return redirect("match", slug=slug, match_id=match.id)
        except DomainError as exc:
            form.add_error(None, str(exc))
            match.refresh_from_db()
    return render(request, "match.html", {"event": event, "match": match, "caps": caps, "form": form, "correction": correction,
        "courts": event.courts.all(), "results": match.results.order_by("-revision"), "submission": match.results.filter(status="submitted").first(),
        "call_overdue": bool(match.called_at and match.status == "called" and timezone.now() >= match.called_at + timedelta(minutes=10)), "scorer_grants": event.grants.filter(role="scorer").select_related("user"), "descendants": services.descendants_of(match)})


@login_required
@require_POST
def division_command(request, slug, division_id):
    event, caps = event_access(request, slug, public=False)
    action = request.POST.get("action")
    if action not in ("qualify", "finalize"):
        raise DomainError("Unsupported division action.")
    fn = services.qualify_pools if action == "qualify" else services.finalize
    fn(event.id, request.user, {"division": str(division_id), "event_revision": request.POST.get("revision", -1)}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=results")


@login_required
@require_POST
def court_command(request, slug, court_id):
    event, caps = event_access(request, slug, public=False)
    from .operations import court_update
    court_update(event.id, request.user, {"court": str(court_id), "status": request.POST.get("status"), "notes": request.POST.get("notes", ""), "event_revision": request.POST.get("revision", -1)}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=courts")


@login_required
@require_POST
def finance_command(request, slug):
    event, caps = event_access(request, slug, public=False)
    try:
        amount = int(request.POST.get("amount_cents", "0"))
    except ValueError:
        raise DomainError("Enter the amount as whole cents.")
    services.record_receipt(event.id, request.user, {"event_revision": request.POST.get("revision", -1), "entry": request.POST["entry"], "amount_cents": amount,
        "kind": request.POST["kind"], "method": request.POST.get("method", ""), "reference": request.POST.get("reference", "")}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=finance")


@login_required
@require_POST
def sanction_command(request, slug):
    event, caps = event_access(request, slug, public=False)
    services.sanction_evidence(event.id, request.user, {**{k: request.POST.get(k, "") for k in ("status", "body", "reference", "notes")}, "event_revision": request.POST.get("revision", -1)}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=sanction")


@login_required
@require_POST
def staff_command(request, slug):
    from .operations import staff_update
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "staff")
    rate_limit(request, "staff_action", limit=30)
    data = {k: request.POST.get(k, "") for k in ("action", "grant", "invite", "email", "role")}
    data["event_revision"] = request.POST.get("revision", -1)
    staff_update(event.id, request.user, data, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=staff")


def flyer(request, slug):
    event, caps = event_access(request, slug)
    return render(request, "flyer.html", {"event": event, "divisions": event.divisions.all()})


def qr(request, slug):
    event, caps = event_access(request, slug)
    if event.visibility == "private":
        require(request.user, event, "promote")
    buffer = io.BytesIO()
    qrcode.make(f"{settings.SITE_URL}/events/{event.slug}/", box_size=6, border=4).save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
def print_pack(request, slug):
    event, caps = event_access(request, slug, public=False)
    require(request.user, event, "operate")
    return render(request, "print_pack.html", {"event": event, "entries": Entry.objects.filter(division__event=event, status="admitted").select_related("division").prefetch_related("members__participant"),
        "matches": services.current_matches(event).select_related("side_a", "side_b", "court", "division"), "generated_at": timezone.now()})
