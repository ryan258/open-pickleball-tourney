"""All event mutations serialize on the event row (SQLite: BEGIN IMMEDIATE)."""
import hashlib
import json
import secrets
import uuid
from datetime import date, timedelta
from functools import wraps
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .engine import DomainError, round_robin, elimination_graph, snake_pools, validate_games, rank_round_robin
from .models import (Event, Court, Division, Participant, Entry, EntryMember, Draw, Match, Result,
                     Audit, Operation, Outbox, Token, Receipt)
from .permissions import require, require_match

TERMINAL = {"completed", "bye", "void"}
ACTIVE = {"called", "in_progress", "suspended", "awaiting_confirmation"}


def integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise DomainError("Enter a valid whole number or reload the form.")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def audit(event, actor, action, detail):
    Audit.objects.create(event=event, actor=actor if actor and actor.is_authenticated else None,
                         action=action, detail=detail, event_revision=event.revision)


def command(action, capability=None, archived_ok=False):
    def decorator(fn):
        @wraps(fn)
        def wrapped(event_id, actor, data, key=None):
            with transaction.atomic():
                event = Event.objects.select_for_update().get(pk=event_id)
                if capability:
                    require(actor, event, capability)
                actor_key = str(actor.pk) if actor and actor.is_authenticated else "guest"
                try:
                    key = uuid.UUID(str(key)) if key else uuid.uuid4()
                except (ValueError, TypeError, AttributeError):
                    raise DomainError("Invalid action key. Reload the form.")
                if capability == "score" and data.get("match"):
                    require_match(actor, event, scoped(Match, event, data["match"], "division__event"))
                checksum = digest(data)
                prior = Operation.objects.filter(event=event, key=key).first()
                if prior:
                    if (prior.digest, prior.action, prior.actor_key) != (checksum, action, actor_key):
                        raise DomainError("This action key was already used with different input.", "key_conflict", 409)
                    return prior.result
                if event.status in ("archived", "cancelled") and not archived_ok:
                    raise DomainError("This event is closed to ordinary changes.", "closed", 409)
                if "event_revision" in data and integer(data["event_revision"]) != event.revision:
                    raise DomainError("The event changed in another window. Refresh and review before retrying.", "stale", 409)
                result = fn(event, actor, data) or {}
                event.revision += 1
                event.save()
                audit(event, actor, action, {k: v for k, v in result.items() if k in ("id", "status", "count", "revision", "match", "unscheduled")})
                Operation.objects.create(event=event, key=key, actor_key=actor_key, action=action, digest=checksum, result=result)
                return result
        return wrapped
    return decorator


def issue_token(kind, email, event=None, payload=None, hours=24):
    raw = secrets.token_urlsafe(32)
    token = Token.objects.create(kind=kind, email=email.lower().strip(), event=event, payload=payload or {},
                                 digest=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now()+timedelta(hours=hours))
    return raw, token


def queue_mail(event, recipient, subject, body, key, marketing=False):
    if recipient and (event is None or event.external_actions_enabled):
        Outbox.objects.get_or_create(key=key, defaults={"event": event, "recipient": recipient,
            "subject": subject, "body": body, "marketing": marketing})


def notify_entry(entry, subject, text, suffix):
    event = entry.division.event
    if not event.external_actions_enabled:
        return
    for member in entry.members.filter(active=True).select_related("participant"):
        p = member.participant
        if p.email:
            raw, token = issue_token("manage", p.email, event, {"participant": str(p.id)}, hours=72)
            queue_mail(event, p.email, subject, f"{text}\n\nManage your entry: {settings.SITE_URL}/link/{raw}/",
                       f"entry:{entry.id}:{event.revision+1}:{suffix}:{p.id}")


def scoped(model, event, pk, relation="event"):
    try:
        return model.objects.get(pk=pk, **{relation: event})
    except (model.DoesNotExist, ValueError, TypeError, ValidationError):
        raise DomainError("That item is unavailable in this event.", "not_found", 404)


def current_matches(event):
    return Match.objects.filter(division__event=event, draw_version=F("division__draw_version"))


def division_matches(division):
    return division.matches.filter(draw_version=division.draw_version)


def rules(division):
    return division.rules_snapshot or {"target": division.target, "best_of": division.best_of, "format": division.format}


def ensure_revision(match, data):
    if integer(data.get("revision", -1)) != match.revision:
        raise DomainError("This match changed. Review the latest version before continuing.", "stale", 409)
    if match.draw_version != match.division.draw_version:
        raise DomainError("This match belongs to an older draw.", "old_draw", 409)


def eligible(participant, division):
    day = division.event.start_at.astimezone(ZoneInfo(division.event.time_zone)).date()
    age = day.year-participant.birth_date.year-((day.month, day.day) < (participant.birth_date.month, participant.birth_date.day))
    if age < max(18, division.min_age) or (division.max_age is not None and age > division.max_age):
        raise DomainError(f"{participant.name} is outside this division's age range. Junior registration is not enabled.")
    if participant.birth_date > day:
        raise DomainError("Birth date must precede the event.")


def occupancy(division):
    return division.entries.filter(Q(status="admitted") | Q(status="offered", offer_expires__gt=timezone.now())).count()


def try_admit(entry):
    division = entry.division
    members = list(entry.members.filter(active=True).select_related("participant"))
    if len(members) != division.team_size or any(not m.accepted_at for m in members):
        entry.status = "incomplete"
    else:
        for member in members:
            eligible(member.participant, division)
        ratings = [m.participant.skill for m in members]
        if division.skill_min is not None or division.skill_max is not None:
            if any(r is None for r in ratings):
                raise DomainError("A declared skill level is required for this division.")
            rating = max(ratings)
            if (division.skill_min is not None and rating < division.skill_min) or (division.skill_max is not None and rating >= division.skill_max):
                raise DomainError("The team's highest skill must fall in the published band (minimum inclusive, maximum exclusive).")
        if division.draw_locked:
            raise DomainError("The draw is locked; new admission requires a director-reviewed replacement draw.")
        if entry.status == "admitted":
            return
        if entry.status == "offered" and entry.offer_expires and entry.offer_expires > timezone.now():
            entry.status = "admitted"
        elif occupancy(division) < division.capacity and not division.entries.filter(status="waitlisted", offer_paused=False).exclude(pk=entry.pk).exists():
            entry.status = "admitted"
        elif division.waitlist_enabled:
            entry.status = "waitlisted"
            entry.queue_at = timezone.now()
        else:
            raise DomainError("This division is full and its waitlist is closed.", "full", 409)
        entry.offer_expires = None
    entry.save()


def advance_waitlist(division):
    now = timezone.now()
    for expired in division.entries.filter(status="offered", offer_expires__lte=now):
        expired.status = "waitlisted"; expired.offer_paused = True
        expired.queue_at = now; expired.offer_expires = None; expired.save()
        notify_entry(expired, "Your waitlist offer expired", "Your entry is paused on the waitlist. Contact the director to rejoin.", "expired")
    if not division.event.registration_is_open or division.draw_locked:
        return
    while occupancy(division) < division.capacity:
        entry = division.entries.filter(status="waitlisted", offer_paused=False).order_by("queue_at", "id").first()
        if not entry:
            break
        entry.status = "offered"
        entry.offer_expires = min(now+timedelta(hours=24), division.event.registration_close)
        entry.save()
        notify_entry(entry, "A spot is available", f"Accept your reserved spot before {entry.offer_expires.astimezone(ZoneInfo(division.event.time_zone))}.", "offer")


@command("register")
def register(event, actor, data):
    assisted = bool(data.get("assisted"))
    if assisted:
        require(actor, event, "operate")
    elif not event.registration_is_open:
        raise DomainError("Registration is not open for this event.")
    if integer(data.get("policy_version", -1)) != event.policy_version:
        raise DomainError("The policies changed. Review the current policies and accept again.", "policy_changed", 409)
    division = scoped(Division, event, data["division"])
    if division.draw_locked:
        raise DomainError("The draw is locked. Contact the director about admission.")
    advance_waitlist(division)
    people = data["people"]
    if len(people) != division.team_size:
        raise DomainError("Provide exactly one person for singles or two people for doubles.")
    new_count = sum(not p.get("email") or not event.participants.filter(email=p["email"].lower().strip()).exists() for p in people)
    if event.participants.count()+new_count > 128:
        raise DomainError("This installation currently supports 128 participants per event.")
    entry = Entry.objects.create(division=division, label=data["label"], quoted_fee_cents=event.fee_cents,
        quoted_policy={"version": event.policy_version, "participation": event.participation_policy, "refund": event.refund_policy},
        seed=(division.entries.aggregate(n=Max("seed"))["n"] or 0)+1)
    seen = set()
    for i, person in enumerate(people):
        email = person.get("email", "").lower().strip()
        if email and email in seen:
            raise DomainError("Each doubles partner needs a distinct contact identity.")
        seen.add(email)
        participant = Participant.objects.filter(event=event, email=email).first() if email else None
        if not participant:
            participant = Participant(event=event, name=person["name"], email=email,
                birth_date=date.fromisoformat(person["birth_date"]), skill=person.get("skill") or None)
            participant.full_clean(); participant.save()
        elif participant.birth_date.isoformat() != person["birth_date"]:
            raise DomainError("This contact already has an event identity with different details. Contact the director.")
        eligible(participant, division)
        if EntryMember.objects.filter(division=division, participant=participant, active=True).exists():
            raise DomainError(f"{participant.name} already belongs to an active entry in this division.")
        accepted = (assisted and person.get("accepted")) or (not assisted and i == 0)
        EntryMember.objects.create(entry=entry, participant=participant, division=division,
            accepted_at=timezone.now() if accepted else None,
            consent_method="assisted_verbal" if assisted and accepted else "verified_email" if accepted else "",
            policy_version=event.policy_version)
        if not accepted and email and data.get("send_notices", True):
            raw, _ = issue_token("partner", email, event, {"entry": str(entry.id), "participant": str(participant.id)}, hours=168)
            queue_mail(event, email, f"Partner invitation · {event.title}",
                f"You have been invited to join {entry.label}. Review and accept your own terms: {settings.SITE_URL}/link/{raw}/",
                f"partner:{entry.id}:{participant.id}")
    try_admit(entry)
    if data.get("send_notices", True):
        notify_entry(entry, f"Registration: {entry.status}", f"{entry.label} is {entry.status.replace('_', ' ')} in {division.name}.", "registration")
    return {"id": str(entry.id), "status": entry.status}


@command("accept_partner")
def accept_partner(event, actor, data):
    entry = scoped(Entry, event, data["entry"], "division__event")
    member = entry.members.filter(participant_id=data["participant"], active=True).first()
    if not member:
        raise DomainError("This invitation is no longer available.", "expired", 410)
    if integer(data.get("policy_version", -1)) != event.policy_version:
        raise DomainError("The policies changed. Review and accept the current policies.", "policy_changed", 409)
    if not event.registration_is_open or entry.status in ("withdrawn", "rejected"):
        raise DomainError("This invitation is no longer available.")
    member.accepted_at = timezone.now(); member.consent_method = "verified_email"
    member.policy_version = event.policy_version; member.save()
    try_admit(entry)
    notify_entry(entry, "Partner confirmed", f"Your team is now {entry.status}.", "partner_confirmed")
    return {"id": str(entry.id), "status": entry.status}


@command("entry_action")
def entry_action(event, actor, data):
    entry = scoped(Entry, event, data["entry"], "division__event")
    if not data.get("participant"):
        require(actor, event, "operate")
    elif not entry.members.filter(participant_id=data["participant"], active=True).exists():
        raise DomainError("This entry is not yours.", "forbidden", 403)
    action = data["action"]
    if action == "accept_offer":
        if entry.status != "offered" or not entry.offer_expires or entry.offer_expires <= timezone.now() or not event.registration_is_open:
            raise DomainError("This offer has expired. Ask the director to rejoin the queue.")
        try_admit(entry)
    elif action == "withdraw":
        if division_matches(entry.division).filter(Q(side_a=entry) | Q(side_b=entry), status__in=ACTIVE).exists():
            raise DomainError("Resolve the active match before withdrawing this entry.")
        entry.status = "withdrawn"; entry.offer_expires = None
        entry.withdrawal_reason = data.get("reason", "Participant withdrawal")[:300]
        entry.save()
        notify_entry(entry, "Entry updated", "Your entry has been withdrawn.", "entry_update")  # before members go inactive
        entry.members.update(active=False)
        propagate(entry.division)
        advance_waitlist(entry.division)
    elif action == "rejoin":
        if entry.status != "waitlisted":
            raise DomainError("Only a waitlisted entry can rejoin the offer queue.")
        entry.offer_paused = False; entry.queue_at = timezone.now(); entry.save()
        advance_waitlist(entry.division)
    else:
        raise DomainError("Unsupported entry action.")
    if action != "withdraw":
        notify_entry(entry, "Entry updated", f"Your entry is now {entry.status}.", "entry_update")
    return {"id": str(entry.id), "status": entry.status}


@command("check_in", "operate")
def check_in(event, actor, data):
    member = scoped(EntryMember, event, data["member"], "division__event")
    if not member.active or member.entry.status != "admitted" or not member.accepted_at:
        raise DomainError("Admission and participation acceptance must be complete before check-in.")
    eligible(member.participant, member.division)
    want = bool(data.get("checked_in", True))
    if not want and division_matches(member.division).filter(Q(side_a=member.entry) | Q(side_b=member.entry), status__in=ACTIVE).exists():
        raise DomainError("Resolve this entry's active match before undoing check-in.")
    member.checked_in = want
    member.checked_in_at = timezone.now() if member.checked_in else None
    member.save()
    return {"id": str(member.id), "status": "checked_in" if member.checked_in else "expected"}


@command("event_action", "edit", archived_ok=True)
def event_action(event, actor, data):
    action = data["action"]
    if event.status in ("archived", "cancelled") and action != "archive":
        raise DomainError("This event is closed to ordinary changes.", "closed", 409)
    if action == "publish":
        if event.status not in ("draft", "published"):
            raise DomainError("A cancelled or archived event cannot be republished.")
        if not event.divisions.exists() or not event.courts.exists():
            raise DomainError("Add at least one division and court before publishing.")
        if not all((event.title, event.venue, event.address, event.contact_email, event.participation_policy, event.refund_policy)):
            raise DomainError("Complete the venue, contact, participation, and refund information.")
        if not event.start_at < event.end_at or not event.registration_open < event.registration_close <= event.end_at:
            raise DomainError("Check the event and registration date ranges.")
        event.status = "published"
    elif action == "hold":
        if event.status != "published" or not data.get("reason", "").strip():
            raise DomainError("A published event and hold reason are required.")
        event.hold_reason = data["reason"][:300]; event.competition = "suspended"
    elif action == "resume":
        if event.status != "published":
            raise DomainError("Only a published event can resume.")
        event.hold_reason = ""; event.competition = "live"
    elif action == "close_registration":
        event.registration_close = timezone.now()
        for division in event.divisions.all():
            division.entries.filter(status="offered").update(offer_expires=timezone.now())
            advance_waitlist(division)
    elif action == "cancel":
        if not data.get("reason", "").strip():
            raise DomainError("Give participants a reason for cancellation.")
        if current_matches(event).filter(status__in=ACTIVE).exists():
            raise DomainError("Resolve or void active matches before cancelling.")
        event.status = "cancelled"; event.cancellation_reason = data["reason"]
        event.registration_close = timezone.now()
        event.divisions.all().update(status="partial")
        Entry.objects.filter(division__event=event, status="offered").update(status="waitlisted", offer_expires=None, offer_paused=True)
    elif action == "archive":
        if current_matches(event).exclude(status__in=TERMINAL).exists() and event.status != "cancelled":
            raise DomainError("Complete or cancel competition before archiving.")
        event.status = "archived"
    elif action == "announce":
        message = data.get("message", "").strip()
        if not message or len(message) > 2000:
            raise DomainError("Write an announcement of 1–2,000 characters.")
        event.notices = [{"text": message, "at": timezone.now().isoformat(), "revision": event.revision+1}, *event.notices][:50]
    else:
        raise DomainError("Unsupported event action.")
    if action in ("hold", "resume", "cancel", "announce"):
        message = data.get("message") or data.get("reason") or "Play is resuming. Check the current court board."
        for entry in Entry.objects.filter(division__event=event, status__in=["admitted", "waitlisted", "offered"]):
            notify_entry(entry, f"{event.title}: {action.replace('_', ' ')}", message, action)
    return {"status": event.status, "revision": event.revision+1}


def draw_inputs(division, random_seed=""):
    import random
    entries = list(division.entries.filter(status="admitted").order_by("seed", "created_at"))
    if not 2 <= len(entries) <= min(16, division.capacity):
        raise DomainError("Admit 2–16 entries within this division's capacity before generating a draw.")
    if random_seed:
        random.Random(random_seed).shuffle(entries)
    return {"entries": [str(e.id) for e in entries], "random_seed": random_seed,
            "format": division.format, "target": division.target, "best_of": division.best_of,
            "pool_count": division.pool_count, "qualifiers": division.qualifiers,
            "ranking": "casual-v1", "withdrawal": "preserve-played-walkover-future", "version": 1}


def add_elimination(division, entry_ids, number=1, stage_override=None):
    nodes = elimination_graph(entry_ids, double=division.format == "double_elimination")
    created = []
    for node in nodes:
        attrs = {}
        for slot in ("a", "b"):
            value = node[slot]
            if isinstance(value, tuple):
                attrs[f"source_{slot}"] = created[value[0]]
                attrs[f"source_{slot}_outcome"] = value[1]
            else:
                attrs[f"side_{slot}_id"] = value
        created.append(Match.objects.create(division=division, draw_version=division.draw_version,
            number=number+len(created), stage=stage_override or node["stage"], round=node["round"], **attrs))
    return created


@command("lock_draw", "edit")
def lock_draw(event, actor, data):
    division = scoped(Division, event, data["division"])
    if division_matches(division).filter(Q(started_at__isnull=False) | Q(status="completed")).exists():
        raise DomainError("Play has started. Use a correction or withdrawal; do not regenerate this draw.")
    inputs = draw_inputs(division, data.get("random_seed", ""))
    if data.get("preview_digest") != digest(inputs):
        raise DomainError("The admitted roster or settings changed. Preview the draw again.", "stale", 409)
    # Prior draw records are retained. Old calls no longer reserve resources.
    division_matches(division).filter(status="called").update(status="ready", called_at=None, court=None)
    division.draw_version += 1; division.draw_locked = True; division.rules_snapshot = inputs
    division.status = "provisional"; division.final_snapshot = []; division.save()
    Draw.objects.create(division=division, version=division.draw_version, inputs=inputs, digest=digest(inputs))
    for seed, entry_id in enumerate(inputs["entries"], 1):
        division.entries.filter(pk=entry_id).update(seed=seed, pool="")
    if division.format in ("single_elimination", "double_elimination"):
        add_elimination(division, inputs["entries"])
    else:
        groups = snake_pools(inputs["entries"], division.pool_count) if division.format == "pools" else [inputs["entries"]]
        if division.format == "pools" and division.qualifiers > min(map(len, groups)):
            raise DomainError("Qualifiers per pool cannot exceed the smallest pool.")
        number = 1
        for pi, group in enumerate(groups):
            pool = chr(65+pi) if division.format == "pools" else ""
            division.entries.filter(pk__in=group).update(pool=pool)
            for ri, pairs in enumerate(round_robin(group), 1):
                for a, b in pairs:
                    Match.objects.create(division=division, draw_version=division.draw_version, number=number,
                        round=ri, stage="pool" if pool else "round_robin", pool=pool, side_a_id=a, side_b_id=b, status="ready")
                    number += 1
    propagate(division)
    return {"id": str(division.id), "count": division_matches(division).count(), "revision": division.draw_version}


def propagate(division):
    """Topological propagation. Started/confirmed matches are changed only by correction workflow."""
    for match in division_matches(division).select_related("side_a", "side_b", "source_a", "source_b"):
        if match.status in ACTIVE or match.status == "completed":
            continue
        if match.incident:
            continue
        resolved = True
        for slot in ("a", "b"):
            source = getattr(match, f"source_{slot}")
            if source:
                source.refresh_from_db()
                if source.status not in TERMINAL:
                    resolved = False; value = None
                elif getattr(match, f"source_{slot}_outcome") == "winner":
                    value = source.winner
                else:
                    value = (source.side_b if source.winner_id == source.side_a_id else source.side_a) if source.winner_id and source.side_a_id and source.side_b_id else None
                setattr(match, f"side_{slot}", value)
        if match.stage == "reset" and match.source_a:
            final = match.source_a
            final.refresh_from_db()
            if final.status in TERMINAL and (not final.side_b_id or final.winner_id != final.side_b_id):
                match.status = "void"; match.winner = None; match.outcome = "reset_not_needed"; match.save(); continue
        if not resolved:
            match.status = "blocked"; match.winner = None
        elif not match.side_a_id or not match.side_b_id:
            match.status = "bye"; match.winner = match.side_a or match.side_b; match.outcome = "bye"
        else:
            a_out = match.side_a.status == "withdrawn"
            b_out = match.side_b.status == "withdrawn"
            if a_out or b_out:
                winner = None if a_out and b_out else match.side_b if a_out else match.side_a
                match.status = "completed" if winner else "void"; match.winner = winner
                match.outcome = "walkover" if winner else "void"
                match.results.filter(status="confirmed").update(status="superseded")
                Result.objects.create(match=match, revision=(match.results.aggregate(n=Max("revision"))["n"] or 0)+1,
                    status="confirmed", winner=winner, outcome=match.outcome, games=[],
                    reason="Withdrawal under the published casual policy", confirmed_at=timezone.now())
            else:
                match.status = "ready"; match.winner = None; match.outcome = ""
        match.save()


def standings(division, pool=None):
    inputs = division.rules_snapshot.get("entries", [])
    entries = division.entries.filter(pk__in=inputs).order_by("seed") if inputs else division.entries.filter(status="admitted").order_by("seed")
    if pool is not None:
        entries = entries.filter(pool=pool)
    records = [{"id": str(e.id), "label": e.label, "seed": e.seed, "status": e.status} for e in entries]
    results = []
    matches = division_matches(division)
    if division.format in ("round_robin", "pools"):
        matches = matches.filter(stage__in=["round_robin", "pool"])
        if pool is not None:
            matches = matches.filter(pool=pool)
    for match in matches.filter(status="completed").select_related("side_a", "side_b"):
        result = match.current_result
        if result:
            results.append({"a": str(match.side_a_id), "b": str(match.side_b_id), "winner": str(match.winner_id) if match.winner_id else None,
                            "outcome": result.outcome, "games": result.games})
    if division.format in ("round_robin", "pools") and (pool is not None or not division_matches(division).filter(stage="playoff").exists()):
        return rank_round_robin(records, results)
    finals = division_matches(division).filter(stage__in=["winners", "playoff", "final", "reset"]).exclude(status="void").order_by("-number")
    final = finals.first()
    for row in records:
        row.update(rank=None, wins=sum(r["winner"] == row["id"] for r in results), played=sum(row["id"] in [r["a"], r["b"]] for r in results),
                   differential=0, points_for=0, tie_break="Elimination result")
        if final and final.status == "completed":
            if str(final.winner_id) == row["id"]:
                row["rank"] = 1
            elif row["id"] in [str(final.side_a_id), str(final.side_b_id)]:
                row["rank"] = 2
    return sorted(records, key=lambda r: (r["rank"] or 999, -r["wins"], r["seed"]))


@command("qualify_pools", "finalize")
def qualify_pools(event, actor, data):
    division = scoped(Division, event, data["division"])
    if division.format != "pools" or not division.draw_locked:
        raise DomainError("Generate the pool draw first.")
    matches = division_matches(division)
    if matches.filter(stage="playoff").exists() or matches.exclude(status__in=TERMINAL).exists():
        raise DomainError("Complete every pool match before qualifying. A playoff can only be generated once.")
    pools = sorted(set(division.entries.exclude(pool="").values_list("pool", flat=True)))
    ranks = {p: standings(division, p) for p in pools}
    qualifiers = [ranks[p][place]["id"] for place in range(division.rules_snapshot["qualifiers"]) for p in pools]
    add_elimination(division, qualifiers, (matches.aggregate(n=Max("number"))["n"] or 0)+1, "playoff")
    propagate(division)
    return {"id": str(division.id), "count": len(qualifiers)}


def schedule_facts(event):
    """One query each for who plays in which entry and per-person rest/availability, so interval checks stay in memory."""
    entries = {}
    for entry_id, person_id in EntryMember.objects.filter(division__event=event, active=True).values_list("entry_id", "participant_id"):
        entries.setdefault(entry_id, set()).add(person_id)
    return {"entries": entries, "people": {p.id: p for p in event.participants.all()}}


def people_ids(match, facts=None):
    if facts is not None:
        return facts["entries"].get(match.side_a_id, set()) | facts["entries"].get(match.side_b_id, set())
    return set(EntryMember.objects.filter(entry_id__in=[match.side_a_id, match.side_b_id], active=True).values_list("participant_id", flat=True))


def rest_for(event, people, facts=None):
    if facts is not None:
        extra = max((facts["people"][p].extra_rest_minutes for p in people if p in facts["people"]), default=0)
    else:
        extra = Participant.objects.filter(id__in=people).aggregate(n=Max("extra_rest_minutes"))["n"] or 0
    return timedelta(minutes=event.rest_minutes+extra)


def reservations(event, matches):
    now = timezone.now()
    output = []
    for match in matches:
        if not match.court_id:
            continue
        if match.status in ACTIVE:
            start = match.started_at or match.called_at or now
            end = max(match.scheduled_end or now, now+timedelta(minutes=event.duration_minutes))
        elif match.ended_at:
            start = match.started_at or match.ended_at
            end = match.ended_at
        elif match.scheduled_at and match.scheduled_end:
            start, end = match.scheduled_at, match.scheduled_end
        else:
            continue
        output.append((match, match.court, start, end))
    return output


def interval_check(event, match, court, start, end, scheduled, ignore_id=None, facts=None):
    if court.event_id != event.id or court.status != "available":
        raise DomainError("This court is blocked or closed.")
    if start < court.opens_at or end > court.closes_at or start < event.start_at or end > event.end_at:
        raise DomainError("The match falls outside event or court availability.")
    people = people_ids(match, facts)
    rest = rest_for(event, people, facts)
    for person in (Participant.objects.filter(pk__in=people) if facts is None else [facts["people"][p] for p in people if p in facts["people"]]):
        for interval in person.unavailable:
            left, right = parse_datetime(interval["start"]), parse_datetime(interval["end"])
            if left < end and right > start:
                raise DomainError("A participant is unavailable during this interval.")
    for other, other_court, other_start, other_end in scheduled:
        if other.id == (ignore_id or match.id):
            continue
        if court.id == other_court.id and start < other_end+timedelta(minutes=event.buffer_minutes) and end+timedelta(minutes=event.buffer_minutes) > other_start:
            raise DomainError("Another match occupies this court or its turnaround buffer.")
        shared = people & people_ids(other, facts)
        if shared:
            shared_rest = rest_for(event, shared, facts)
            if start < other_end+shared_rest and end+shared_rest > other_start:
                raise DomainError("A player is already scheduled or needs more rest.")


def schedule_proposal(event, start):
    matches = list(current_matches(event).select_related("division", "court", "side_a", "side_b").order_by("division__created_at", "number"))
    courts = list(event.courts.filter(status="available"))
    scheduled = reservations(event, [m for m in matches if m.pinned or m.status in ACTIVE or m.ended_at])
    facts = schedule_facts(event)
    proposal, unscheduled = [], []
    # ponytail: first-fit rescans from the event start per match; fine for the 24-match demo, needs a per-court free-time cursor for a full 8-division event.
    for match in matches:
        if match.status not in ("ready",) or match.pinned:
            continue
        cursor = max(start, event.start_at)
        placed = False
        last_error = "No court is available."
        while cursor < event.end_at and not placed:
            end = cursor+timedelta(minutes=event.duration_minutes)
            for court in courts:
                try:
                    interval_check(event, match, court, cursor, end, scheduled, facts=facts)
                except DomainError as exc:
                    last_error = str(exc); continue
                scheduled.append((match, court, cursor, end))
                proposal.append({"match": str(match.id), "court": str(court.id), "start": cursor.isoformat(), "end": end.isoformat(), "revision": match.revision})
                placed = True; break
            cursor += timedelta(minutes=5)
        if not placed:
            unscheduled.append({"match": match.code, "reason": last_error})
    return {"assignments": proposal, "unscheduled": unscheduled, "event_revision": event.revision}


@command("commit_schedule", "operate")
def commit_schedule(event, actor, data):
    assignments = data["assignments"]
    ids = [x["match"] for x in assignments]
    if len(set(ids)) != len(ids):
        raise DomainError("A schedule cannot assign a match twice.")
    scheduled = reservations(event, current_matches(event).exclude(pk__in=ids).select_related("court"))
    facts = schedule_facts(event)
    for item in assignments:
        match = scoped(Match, event, item["match"], "division__event")
        ensure_revision(match, item)
        if match.status != "ready":
            raise DomainError("Only ready, uncalled matches can be scheduled.")
        court = scoped(Court, event, item["court"])
        start, end = parse_datetime(item["start"]), parse_datetime(item["end"])
        if not start or not end or not timezone.is_aware(start) or not timezone.is_aware(end) or end <= start:
            raise DomainError("Choose a valid, time-zone-aware interval.")
        interval_check(event, match, court, start, end, scheduled, facts=facts)
        match.court = court; match.scheduled_at = start; match.scheduled_end = end
        match.pinned = bool(item.get("pinned", False)); match.revision += 1; match.save()
        scheduled.append((match, court, start, end))
    return {"count": len(assignments)}


@command("match_action", "operate")
def match_action(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event")
    ensure_revision(match, data)
    action = data["action"]
    if action in ("call", "start", "resume"):
        if event.hold_reason or event.status != "published":
            raise DomainError("Publish the event and clear its hold before starting play.")
        allowed = {"call": {"ready"}, "start": {"ready", "called"}, "resume": {"suspended"}}
        if match.status not in allowed[action] or match.incident:
            raise DomainError("This match is not ready for that action.")
        if not match.side_a_id or not match.side_b_id or not match.side_a.checked_in or not match.side_b.checked_in:
            raise DomainError("Both entries must be admitted and fully checked in.")
        if match.side_a.status != "admitted" or match.side_b.status != "admitted":
            raise DomainError("Both entries must still be admitted.")
        court = scoped(Court, event, data.get("court") or match.court_id)
        if court.status != "available":
            raise DomainError("This court is blocked or closed.")
        now = timezone.now()
        if not (court.opens_at <= now < court.closes_at):
            raise DomainError("The court is outside its operating hours.")
        people = people_ids(match)
        others = current_matches(event).exclude(pk=match.pk)
        for other in others.filter(status__in=ACTIVE):
            if other.court_id == court.id or people & people_ids(other):
                raise DomainError("The court or a player is reserved by another active match.", "resource_conflict", 409)
        for other in others.filter(ended_at__isnull=False):
            shared = people & people_ids(other)
            if shared and other.ended_at+rest_for(event, shared) > now:
                raise DomainError("A player needs more rest before the next match.")
            if other.court_id == court.id and other.ended_at+timedelta(minutes=event.buffer_minutes) > now:
                raise DomainError("This court is still in its turnaround buffer.")
        for person in Participant.objects.filter(pk__in=people):
            if any(parse_datetime(i["start"]) <= now < parse_datetime(i["end"]) for i in person.unavailable):
                raise DomainError("A participant is unavailable right now.")
        match.court = court
        if action == "call":
            match.status = "called"; match.called_at = now
            for entry in [match.side_a, match.side_b]:
                notify_entry(entry, f"Court call · {match.code}", f"Please go to {court.name}: {match.label}.", f"call:{match.id}")
        else:
            match.status = "in_progress"; match.started_at = match.started_at or now
            event.competition = "live"
    elif action == "recall" and match.status == "called":
        match.status = "ready"; match.called_at = None
    elif action == "suspend" and match.status == "in_progress":
        match.status = "suspended"
    elif action == "void":
        require(actor, event, "correct")
        if not data.get("reason", "").strip():
            raise DomainError("A reason is required to void a match.")
        descendants = descendants_of(match)
        if any(m.status in ACTIVE or m.status == "completed" for m in descendants):
            raise DomainError("Void affected descendants first, in reverse match order.")
        match.results.filter(status="confirmed").update(status="superseded")
        Result.objects.create(match=match, revision=(match.results.aggregate(n=Max("revision"))["n"] or 0)+1,
            outcome="void", status="confirmed", reason=data["reason"], submitted_by=actor, confirmed_by=actor, confirmed_at=timezone.now())
        match.status = "void"; match.winner = None; match.outcome = "void"; match.ended_at = timezone.now()
        match.incident = data["reason"]
        if match.division.status == "final":
            match.division.status = "reopened"; match.division.save()
        event.competition = "live"
        event.packages.update(status="correction_required")
    else:
        raise DomainError("This transition is not available from the match's current state.")
    match.revision += 1; match.save()
    return {"match": str(match.id), "status": match.status, "revision": match.revision}


@command("submit_score", "score")
def submit_score(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event")
    require_match(actor, event, match)
    ensure_revision(match, data)
    if match.status not in ("ready", "called", "in_progress", "suspended", "awaiting_confirmation") or match.incident:
        raise DomainError("This match cannot accept a new score. Use the correction workflow for confirmed results.")
    if not match.side_a_id or not match.side_b_id:
        raise DomainError("Resolve both entries first.")
    outcome = data.get("outcome", "played")
    if outcome == "played" and not match.started_at:
        raise DomainError("Start this match before recording a played result.")
    if outcome == "retirement" and not match.started_at:
        raise DomainError("Use a walkover when play never started.")
    if outcome in ("walkover", "disqualification", "void"):
        require(actor, event, "correct")
    if outcome == "walkover" and match.started_at:
        raise DomainError("Use retirement or disqualification after play has started.")
    if outcome != "played" and not data.get("reason", "").strip():
        raise DomainError("Administrative outcomes require a reason.")
    winner = validate_games(data["games"], rules(match.division)["target"], rules(match.division)["best_of"], outcome, data.get("winner"), data.get("incomplete_game"))
    match.results.filter(status="submitted").update(status="rejected")
    result = Result.objects.create(match=match, revision=(match.results.aggregate(n=Max("revision"))["n"] or 0)+1,
        games=data["games"], incomplete_game=data.get("incomplete_game"), outcome=outcome, winner=getattr(match, f"side_{winner}") if winner else None,
        submitted_by=actor, reason=data.get("reason", ""))
    match.status = "awaiting_confirmation"; match.revision += 1; match.save()
    return {"id": str(result.id), "match": str(match.id), "status": "submitted"}


@command("confirm_score", "score")
def confirm_score(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event")
    ensure_revision(match, data)
    require_match(actor, event, match)
    result = match.results.filter(pk=data["result"], status="submitted").first()
    if not result or match.status != "awaiting_confirmation":
        raise DomainError("This submission is no longer awaiting confirmation.", "stale", 409)
    if result.outcome != "played":
        require(actor, event, "correct")
    result.status = "confirmed"; result.confirmed_by = actor; result.confirmed_at = timezone.now(); result.save()
    match.status = "completed" if result.winner else "void"; match.winner = result.winner; match.outcome = result.outcome
    match.ended_at = timezone.now(); match.revision += 1; match.save()
    propagate(match.division)
    return {"match": str(match.id), "status": match.status, "revision": match.revision}


def descendants_of(match):
    found, frontier = {}, [match.id]
    while frontier:
        children = list(Match.objects.filter(Q(source_a_id__in=frontier) | Q(source_b_id__in=frontier),
                                            division=match.division, draw_version=match.draw_version))
        frontier = []
        for child in children:
            if child.id not in found:
                found[child.id] = child; frontier.append(child.id)
    return sorted(found.values(), key=lambda m: m.number)


@command("open_incident", "correct")
def open_incident(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event")
    ensure_revision(match, data)
    if not data.get("reason", "").strip():
        raise DomainError("Describe the correction incident.")
    ids = [match.id, *[m.id for m in descendants_of(match)]]
    Match.objects.filter(pk__in=ids).update(incident=data["reason"][:2000])
    if match.division.status == "final":
        match.division.status = "reopened"; match.division.save()
    return {"match": str(match.id), "count": len(ids)}


@command("correct_score", "correct", archived_ok=True)
def correct_score(event, actor, data):
    match = scoped(Match, event, data["match"], "division__event")
    ensure_revision(match, data)
    if match.status not in ("completed", "void") or not data.get("reason", "").strip():
        raise DomainError("Choose a confirmed match and explain the correction.")
    if match.stage == "pool" and division_matches(match.division).filter(stage="playoff").exists():
        raise DomainError("Pool qualification is already published. A director must resolve the playoff qualification before correcting this pool result.", "qualification_locked", 409)
    descendants = descendants_of(match)
    if any(m.status in ACTIVE or m.status == "completed" for m in descendants):
        raise DomainError("A downstream match has started. Open an incident, then void affected descendants in reverse order before correcting.", "downstream_started", 409)
    outcome = data.get("outcome", "played")
    winner = validate_games(data["games"], rules(match.division)["target"], rules(match.division)["best_of"], outcome, data.get("winner"), data.get("incomplete_game"))
    match.results.filter(status__in=["confirmed", "submitted"]).update(status="superseded")
    Result.objects.create(match=match, revision=(match.results.aggregate(n=Max("revision"))["n"] or 0)+1,
        status="confirmed", games=data["games"], incomplete_game=data.get("incomplete_game"), outcome=outcome, winner=getattr(match, f"side_{winner}") if winner else None,
        reason=data["reason"], submitted_by=actor, confirmed_by=actor, confirmed_at=timezone.now())
    match.winner = getattr(match, f"side_{winner}") if winner else None
    match.status = "completed" if winner else "void"; match.outcome = outcome; match.incident = ""; match.revision += 1; match.save()
    for child in descendants:
        child.results.filter(status__in=["confirmed", "submitted"]).update(status="superseded")
        child.status = "blocked"; child.winner = None; child.court = None; child.called_at = None
        child.scheduled_at = None; child.scheduled_end = None; child.started_at = None; child.ended_at = None
        child.incident = ""; child.outcome = ""; child.revision += 1; child.save()
    division = match.division
    division.status = "reopened" if division.status == "final" else "provisional"; division.save()
    event.packages.update(status="correction_required")
    event.competition = "live"
    propagate(division)
    for entry in division.entries.filter(pk__in=division.rules_snapshot.get("entries", [])):
        notify_entry(entry, "Results corrected", f"{match.code} has a corrected result. Check the updated draw and schedule.", f"correction:{match.id}")
    return {"match": str(match.id), "revision": match.revision}


@command("finalize", "finalize")
def finalize(event, actor, data):
    division = scoped(Division, event, data["division"])
    matches = division_matches(division)
    if not division.draw_locked or not matches.exists() or matches.exclude(status__in=TERMINAL).exists() or matches.exclude(incident="").exists():
        raise DomainError("Resolve all matches and incidents before certification.")
    if division.format == "pools" and not matches.filter(stage="playoff").exists():
        raise DomainError("Generate and finish the playoffs first.")
    if matches.filter(outcome="void").exists():
        raise DomainError("This competition has void outcomes. Resolve them or publish partial results.")
    division.status = "final"; division.final_snapshot = standings(division); division.save()
    audit(event, actor, "final_snapshot", {"division": str(division.id), "draw": division.draw_version,
        "standings": division.final_snapshot, "result_ids": [str(r.id) for r in Result.objects.filter(match__in=matches, status="confirmed")]})
    if not event.divisions.exclude(status="final").exists():
        event.competition = "completed"
    for entry in division.entries.filter(pk__in=division.rules_snapshot.get("entries", [])):
        notify_entry(entry, "Final results published", f"Results for {division.name} are now final.", "final")
    return {"id": str(division.id), "status": "final"}


@command("record_receipt", "finance", archived_ok=True)
def record_receipt(event, actor, data):
    entry = scoped(Entry, event, data["entry"], "division__event")
    amount = int(data["amount_cents"])
    if amount <= 0 or amount > 10000000 or data["kind"] not in ("payment", "refund"):
        raise DomainError("Enter a positive amount and a payment/refund type.")
    if data["kind"] == "refund" and amount > balance(entry)["received"]:
        raise DomainError("A refund cannot exceed the unrefunded amount recorded as received.")
    if not data.get("reference", "").strip():
        raise DomainError("Add a receipt/reference so this external transaction can be reconciled.")
    receipt = Receipt.objects.create(entry=entry, kind=data["kind"], amount_cents=amount,
        reference=data["reference"][:150], method=data.get("method", "External")[:50], actor=actor)
    return {"id": str(receipt.id), "status": "staff_recorded"}


def balance(entry):
    paid = entry.receipts.filter(kind="payment").aggregate(n=Sum("amount_cents"))["n"] or 0
    refunded = entry.receipts.filter(kind="refund").aggregate(n=Sum("amount_cents"))["n"] or 0
    return {"paid": paid, "refunded": refunded, "received": paid-refunded, "due": max(0, entry.quoted_fee_cents-paid+refunded)}


@command("sanction_evidence", "evidence")
def sanction_evidence(event, actor, data):
    allowed = ("not_requested", "preparing", "submitted", "approved_recorded", "rejected", "expired", "revoked", "review_required")
    if data["status"] not in allowed:
        raise DomainError("Independent approval verification is not connected.")
    if data["status"] == "approved_recorded" and not all(data.get(k, "").strip() for k in ("body", "reference", "notes")):
        raise DomainError("Record the body, approval reference, and evidence/review details.")
    event.sanction_status = data["status"]; event.sanction_body = data.get("body", "")[:100]
    event.sanction_reference = data.get("reference", "")[:150]; event.sanction_notes = data.get("notes", "")
    audit(event, actor, "sanction_record_changed", {"status": event.sanction_status, "reference": event.sanction_reference})
    return {"status": event.sanction_status}
