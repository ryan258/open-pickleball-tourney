"""Versioned allowlisted archives. Auth, tokens and queued deliveries never travel."""
import csv
import io
import json
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from . import models as m, services
from .engine import DomainError, validate_games

SCHEMA = "open-tourney-event/1"
# Every portable field is intentional. Adding a model field never silently exports it.
FIELDS = {
    "event": (m.Event, "title summary start_at end_at time_zone registration_open registration_close visibility status competition venue address accessibility contact_email participation_policy refund_policy policy_version currency fee_cents rest_minutes duration_minutes buffer_minutes revision hold_reason cancellation_reason notices sanction_status sanction_body sanction_reference sanction_notes"),
    "courts": (m.Court, "event name status notes opens_at closes_at"),
    "divisions": (m.Division, "event name discipline format capacity target best_of skill_min skill_max min_age max_age pool_count qualifiers waitlist_enabled draw_version draw_locked rules_snapshot status final_snapshot"),
    "participants": (m.Participant, "event name email birth_date skill skill_source accommodation extra_rest_minutes unavailable marketing_consent marketing_updated_at"),
    "entries": (m.Entry, "division label status seed queue_at offer_expires offer_paused quoted_fee_cents quoted_policy pool withdrawal_reason"),
    "members": (m.EntryMember, "entry participant division active accepted_at consent_method policy_version checked_in checked_in_at"),
    "draws": (m.Draw, "division version inputs digest"),
    "matches": (m.Match, "division draw_version number stage round pool side_a side_b source_a source_b source_a_outcome source_b_outcome status winner outcome court scheduled_at scheduled_end pinned called_at started_at ended_at revision incident"),
    "results": (m.Result, "match revision status games incomplete_game outcome winner confirmed_at reason"),
    "receipts": (m.Receipt, "entry kind amount_cents reference method"),
    "audit": (m.Audit, "event action detail event_revision"),
    "packages": (m.Package, "event kind event_revision digest payload status notes"),
}
RELATIONS = {"courts": "event", "divisions": "event", "participants": "event", "entries": "division__event", "members": "division__event", "draws": "division__event", "matches": "division__event", "results": "match__division__event", "receipts": "entry__division__event", "audit": "event", "packages": "event"}


def json_ready(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def export_archive(event):
    with transaction.atomic():
        event = m.Event.objects.select_for_update().get(pk=event.pk)
        tables = {}
        for name, (model, names) in FIELDS.items():
            objects = [event] if name == "event" else model.objects.filter(**{RELATIONS[name]: event}).order_by("created_at", "id")
            rows = []
            for obj in objects:
                row = {"id": str(obj.id), "created_at": obj.created_at}
                for field_name in names.split():
                    field = model._meta.get_field(field_name)
                    row[field_name] = getattr(obj, field.attname)
                # Attribution travels as inert source evidence, never as an account grant.
                if name in ("audit", "receipts"):
                    row["source_actor"] = str(obj.actor_id) if obj.actor_id else None
                if name == "results":
                    row["source_submitted_by"] = str(obj.submitted_by_id) if obj.submitted_by_id else None
                    row["source_confirmed_by"] = str(obj.confirmed_by_id) if obj.confirmed_by_id else None
                rows.append(json_ready(row))
            tables[name] = rows
        content = {"schema": SCHEMA, "exported_at": timezone.now().isoformat(), "source_event": str(event.id), "event_revision": event.revision,
                   "private_data": True, "external_actions": "excluded", "tables": tables}
        return {"content": content, "sha256": services.digest(content)}


def validate_archive(document):
    try:
        if not isinstance(document, dict) or set(document) != {"content", "sha256"}:
            raise ValueError()
        content = document["content"]
        if content["schema"] != SCHEMA or services.digest(content) != document["sha256"]:
            raise ValueError()
        tables = content["tables"]
        if set(tables) != set(FIELDS) or len(tables["event"]) != 1 or sum(len(rows) for rows in tables.values()) > 15000:
            raise ValueError()
        limits = {"courts": 8, "divisions": 8, "participants": 128, "entries": 1024, "matches": 4096}
        index = {}
        for name, (model, names) in FIELDS.items():
            rows = tables[name]
            if not isinstance(rows, list) or len(rows) > limits.get(name, 15000):
                raise ValueError()
            fields = set(names.split()) | {"id", "created_at"}
            if name in ("audit", "receipts"):
                fields.add("source_actor")
            if name == "results":
                fields.update(("source_submitted_by", "source_confirmed_by"))
            index[name] = {}
            for row in rows:
                if not isinstance(row, dict) or set(row) != fields or str(uuid.UUID(row["id"])) != row["id"] or row["id"] in index[name]:
                    raise ValueError()
                index[name][row["id"]] = row
        all_ids = [key for rows in index.values() for key in rows]
        if len(set(all_ids)) != len(all_ids):
            raise ValueError()
        model_table = {model: name for name, (model, _) in FIELDS.items()}
        for name, (model, names) in FIELDS.items():
            for row in tables[name]:
                for key in names.split():
                    field = model._meta.get_field(key)
                    if field.is_relation and row[key] is not None and row[key] not in index[model_table[field.related_model]]:
                        raise ValueError()
                    if not field.is_relation:
                        field.clean(row[key], None)
        for member in tables["members"]:
            if (member["active"] and index["entries"][member["entry"]]["division"] != member["division"]) or index["participants"][member["participant"]]["event"] != content["source_event"]:
                raise ValueError()
        for match in tables["matches"]:
            if match["winner"] and match["winner"] not in (match["side_a"], match["side_b"]):
                raise ValueError()
            for slot in ("side_a", "side_b", "winner"):
                if match[slot] and index["entries"][match[slot]]["division"] != match["division"]:
                    raise ValueError()
            for slot in ("source_a", "source_b"):
                if match[slot]:
                    source = index["matches"][match[slot]]
                    if source["division"] != match["division"] or source["draw_version"] != match["draw_version"] or source["number"] >= match["number"]:
                        raise ValueError()
        for result in tables["results"]:
            match = index["matches"][result["match"]]
            if result["winner"] and index["entries"][result["winner"]]["division"] != match["division"]:
                raise ValueError()
            if result["status"] == "confirmed" and result["winner"] and result["winner"] not in (match["side_a"], match["side_b"]):
                raise ValueError()
        if tables["event"][0]["id"] != content["source_event"]:
            raise ValueError()
        for d in tables["divisions"]:
            if d["format"] not in dict(m.FORMATS) or d["discipline"] not in ("singles", "doubles") or not 2 <= d["capacity"] <= 16:
                raise ValueError()
        validate_domain(tables, index)
        return content
    except (KeyError, TypeError, ValueError, AttributeError, ValidationError, RecursionError, ZoneInfoNotFoundError):
        raise DomainError("Archive schema, hash, field value, or scoped relationship is invalid. No records were imported.")


def validate_domain(tables, index):
    def instant(value):
        parsed = parse_datetime(value)
        if parsed is None or not timezone.is_aware(parsed):
            raise ValueError()
        return parsed
    def choices(table, field, allowed):
        if any(row[field] not in allowed for row in tables[table]):
            raise ValueError()
    choices("event", "status", {"draft", "published", "archived", "cancelled"})
    choices("courts", "status", {"available", "blocked", "closed"})
    choices("entries", "status", {"incomplete", "admitted", "waitlisted", "offered", "withdrawn", "rejected"})
    choices("matches", "status", {"blocked", "ready", "called", "in_progress", "suspended", "awaiting_confirmation", "completed", "bye", "void"})
    choices("results", "status", {"submitted", "confirmed", "rejected", "superseded"})
    choices("receipts", "kind", {"payment", "refund"})
    event = tables["event"][0]
    ZoneInfo(event["time_zone"])
    if instant(event["end_at"]) <= instant(event["start_at"]) or not 5 <= event["duration_minutes"] <= 240 or not 0 <= event["rest_minutes"] <= 240 or not 0 <= event["buffer_minutes"] <= 60:
        raise ValueError()
    if not isinstance(event["notices"], list) or len(event["notices"]) > 50:
        raise ValueError()
    for notice in event["notices"]:
        if not isinstance(notice, dict) or not isinstance(notice.get("text"), str) or len(notice["text"]) > 2000:
            raise ValueError()
        instant(notice["at"])
    for person in tables["participants"]:
        if not isinstance(person["unavailable"], list) or len(person["unavailable"]) > 30 or not 0 <= person["extra_rest_minutes"] <= 240:
            raise ValueError()
        for interval in person["unavailable"]:
            if not isinstance(interval, dict) or set(interval) != {"start", "end"} or instant(interval["end"]) <= instant(interval["start"]):
                raise ValueError()
    for division in tables["divisions"]:
        rules = division["rules_snapshot"]
        if division["target"] not in (11,15,21) or division["best_of"] not in (1,3) or not isinstance(rules, dict) or not isinstance(division["final_snapshot"], list):
            raise ValueError()
        if rules:
            entries = rules.get("entries")
            if not isinstance(entries, list) or len(set(entries)) != len(entries) or not 2 <= len(entries) <= 16:
                raise ValueError()
            if any(e not in index["entries"] or index["entries"][e]["division"] != division["id"] for e in entries):
                raise ValueError()
            if rules.get("target") not in (11,15,21) or rules.get("best_of") not in (1,3):
                raise ValueError()
    for entry in tables["entries"]:
        if not isinstance(entry["quoted_policy"], dict):
            raise ValueError()
    for draw in tables["draws"]:
        if not isinstance(draw["inputs"], dict) or services.digest(draw["inputs"]) != draw["digest"]:
            raise ValueError()
    for audit in tables["audit"]:
        if not isinstance(audit["detail"], dict):
            raise ValueError()
    for result in tables["results"]:
        division = index["divisions"][index["matches"][result["match"]]["division"]]
        validate_games(result["games"], division["target"], division["best_of"], result["outcome"], "a" if result["winner"] else None, result["incomplete_game"])
    for package in tables["packages"]:
        if not isinstance(package["payload"], dict) or services.digest(package["payload"]) != package["digest"]:
            raise ValueError()


def import_archive(document, organization, actor):
    content = validate_archive(document)
    mapping = {row["id"]: str(uuid.uuid4()) for rows in content["tables"].values() for row in rows}
    def remap(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        return value
    with transaction.atomic():
        saved, deferred = {}, []
        for name, (model, names) in FIELDS.items():
            for row in content["tables"][name]:
                attrs = {"id": mapping[row["id"]], "created_at": row["created_at"]}
                for key in names.split():
                    field = model._meta.get_field(key)
                    value = remap(row[key])
                    attrs[field.attname] = value
                if name == "event":
                    attrs.update(organization=organization, slug=f"restored-{attrs['id'][:12]}", visibility="private", status="draft", external_actions_enabled=False,
                                 sanction_status="review_required", hold_reason="Restored archive: review dates, roster, court states and external evidence before use.")
                if name == "participants":
                    attrs["marketing_consent"] = False
                if name == "matches":
                    deferred.append((attrs["id"], attrs.pop("source_a_id"), attrs.pop("source_b_id")))
                if name == "audit":
                    attrs["detail"] = {**attrs["detail"], "restored_source_actor": row["source_actor"]}
                if name == "packages":
                    attrs["status"] = "restored_evidence"
                    attrs["notes"] = f"Source package digest: {row['digest']}. Restored payload contains remapped IDs."
                    attrs["digest"] = services.digest(attrs["payload"])
                if name == "draws":
                    attrs["digest"] = services.digest(attrs["inputs"])
                obj = model(**attrs)
                obj.full_clean(exclude=[f.name for f in model._meta.fields if f.is_relation], validate_unique=False, validate_constraints=False)
                obj.save(force_insert=True)
                saved[row["id"]] = obj
        for mid, a, b in deferred:
            m.Match.objects.filter(pk=mid).update(source_a_id=a, source_b_id=b)
        event = saved[content["source_event"]]
        services.audit(event, actor, "archive_restored", {"source_event": content["source_event"], "source_sha256": document["sha256"], "source_revision": content["event_revision"], "ownership_remapped": True, "external_actions": "disabled"})
        return event


def public_results(event):
    return {"event": event.title, "event_revision": event.revision, "status": event.status,
        "divisions": [{"name": d.name, "draw_version": d.draw_version, "status": d.status, "standings": services.standings(d),
            "results": [{"match": match.code, "a": match.side_a.label if match.side_a else "", "b": match.side_b.label if match.side_b else "",
                "status": match.status, "outcome": match.outcome, "winner": match.winner.label if match.winner else "",
                "games": match.current_result.games if match.current_result else [], "incomplete_game": match.current_result.incomplete_game if match.current_result else None,
                "revision": match.current_result.revision if match.current_result else None} for match in services.division_matches(d).select_related("side_a", "side_b", "winner")]} for d in event.divisions.all()]}


def csv_text(rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    for row in rows:
        cells = []
        for value in row:
            text = "" if value is None else str(value)
            if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
                text = "'"+text
            cells.append(text)
        writer.writerow(cells)
    return output.getvalue()
