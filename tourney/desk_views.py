import csv
import io
import json
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from . import operations, services, portability
from .engine import DomainError
from .forms import ParticipantForm, EntryEditForm, RegistrationForm, local_instant
from .models import Participant, Entry, Package
from .permissions import require, require_owner
from .views import event_access


def meta(request):
    return {"event_revision": request.POST.get("revision", -1)}


def download(value, filename, kind="application/json"):
    response = HttpResponse(json.dumps(value, indent=2, ensure_ascii=False) if kind == "application/json" else value, content_type=kind)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def clone(request, slug):
    event, _ = event_access(request, slug, public=False)
    result = operations.clone_event(event.id, request.user, meta(request), request.POST.get("operation_key"))
    messages.success(request, "Settings copied into a private draft. Review the fresh dates before publishing.")
    return redirect("desk", slug=result["slug"])


@login_required
def participant_edit(request, slug, participant_id):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "operate")
    person = get_object_or_404(Participant, event=event, pk=participant_id)
    initial = {"accommodation": person.accommodation, "extra_rest_minutes": person.extra_rest_minutes,
               "unavailable": "\n".join(f'{i["start"]} / {i["end"]}' for i in person.unavailable)}
    form = ParticipantForm(request.POST or None, event=event, initial=initial)
    if request.method == "POST" and form.is_valid():
        operations.participant_update(event.id, request.user, {**meta(request), **form.cleaned_data, "participant": str(person.id)}, request.POST.get("operation_key"))
        messages.success(request, "Private accommodations saved. Affected future plans were cleared; preview a new schedule. Review any running match with the players.")
        return redirect(f"/events/{slug}/desk/?tab=entries")
    return render(request, "form_page.html", {"form": form, "event": event, "title": f"Private support for {person.name}", "submit": "Save private accommodations"})


@login_required
def entry_edit(request, slug, entry_id):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "operate")
    entry = get_object_or_404(Entry, division__event=event, pk=entry_id)
    form = EntryEditForm(request.POST or None, entry=entry)
    if request.method == "POST" and form.is_valid():
        data = {**form.cleaned_data, **meta(request), "entry": str(entry.id), "policy_version": request.POST.get("policy_version")}
        data["division"] = str(data["division"].id) if data.get("division") else None
        data["birth_date"] = data["birth_date"].isoformat() if data.get("birth_date") else None
        data["skill"] = str(data["skill"]) if data.get("skill") is not None else None
        try:
            operations.edit_entry(event.id, request.user, data, request.POST.get("operation_key"))
            messages.success(request, "Entry updated. Previous membership and payment evidence is retained.")
            return redirect(f"/events/{slug}/desk/?tab=entries")
        except DomainError as exc:
            form.add_error(None, str(exc))
    return render(request, "form_page.html", {"form": form, "event": event, "show_policy": True, "title": f"Update {entry.label}", "submit": "Save entry change"})


@login_required
@require_POST
def assign_scorer(request, slug, match_id):
    event, _ = event_access(request, slug, public=False)
    operations.assign_scorer(event.id, request.user, {"match": str(match_id), "scorer": request.POST.get("scorer"), "revision": request.POST.get("revision", -1)}, request.POST.get("operation_key"))
    return redirect("match", slug=slug, match_id=match_id)


@login_required
@require_POST
def manual_schedule(request, slug, match_id):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "operate")
    start = local_instant(request.POST.get("start"), ZoneInfo(event.time_zone), request.POST.get("fold", ""))
    end = start+timedelta(minutes=event.duration_minutes)
    services.commit_schedule(event.id, request.user, {"event_revision": request.POST.get("event_revision", -1), "assignments": [{"match": str(match_id), "court": request.POST.get("court"), "revision": request.POST.get("revision"), "start": start.isoformat(), "end": end.isoformat(), "pinned": request.POST.get("pinned") == "on"}]}, request.POST.get("operation_key"))
    return redirect("match", slug=slug, match_id=match_id)


def results_csv(request, slug):
    event, _ = event_access(request, slug)
    rows = [["event", "event_revision", "division", "draw_version", "results_status", "rank", "entry", "wins", "played", "tie_break"]]
    for d in event.divisions.all():
        for row in services.standings(d):
            rows.append([event.title, event.revision, d.name, d.draw_version, d.status, row["rank"], row["label"], row["wins"], row["played"], row["tie_break"]])
    return download(portability.csv_text(rows), f"{slug}-results.csv", "text/csv; charset=utf-8")


@login_required
def roster_csv(request, slug):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "export")
    rows = [["division", "entry", "status", "participant", "checked_in", "event_revision"]]
    for entry in Entry.objects.filter(division__event=event).select_related("division"):
        for member in entry.members.filter(active=True).select_related("participant"):
            rows.append([entry.division.name, entry.label, entry.status, member.participant.name, member.checked_in, event.revision])
    return download(portability.csv_text(rows), f"{slug}-roster.csv", "text/csv; charset=utf-8")


@login_required
def archive_export(request, slug):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "export")
    return download(portability.export_archive(event), f"{slug}-private-archive.json")


class UploadForm(forms.Form):
    file = forms.FileField(label="File")
    def clean_file(self):
        value = self.cleaned_data["file"]
        if value.size > 5*1024*1024:
            raise forms.ValidationError("Use a file no larger than 5 MB.")
        return value


@login_required
def archive_import(request, slug):
    event, _ = event_access(request, slug, public=False); require_owner(request.user, event)  # creates an event in the whole organization
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if not request.POST.get("confirm"):
            form.add_error(None, "Confirm that this private archive is authorized for this organization.")
        else:
            try:
                document = json.loads(form.cleaned_data["file"].read().decode("utf-8"))
                new = portability.import_archive(document, event.organization, request.user)
                messages.success(request, "Archive restored into a private draft. Accounts and staff grants were not imported; email is disabled for this restored event. Review its source evidence before further use.")
                return redirect("desk", slug=new.slug)
            except (ValueError, UnicodeDecodeError, IntegrityError, DomainError, forms.ValidationError) as exc:
                form.add_error(None, str(exc) if isinstance(exc, DomainError) else "Invalid or inconsistent archive. Nothing was imported.")
    return render(request, "upload.html", {"form": form, "event": event, "archive": True, "title": "Restore a private archive"})


@login_required
@require_POST
def package_create(request, slug):
    event, _ = event_access(request, slug, public=False)
    @services.command("package_create", "export", archived_ok=True)
    def create(locked, actor, data):
        payload = portability.public_results(locked)
        package = Package.objects.create(event=locked, event_revision=locked.revision, payload=payload, digest=services.digest(payload))
        return {"id": str(package.id)}
    create(event.id, request.user, meta(request), request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=reports")


@login_required
def package_download(request, slug, package_id):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "export")
    package = get_object_or_404(Package, event=event, pk=package_id)
    return download({"kind": package.kind, "status": package.status, "event_revision": package.event_revision, "sha256": package.digest, "payload": package.payload}, f"{slug}-package-{package.id}.json")


CSV_FIELDS = ["division", "label", "name", "email", "birth_date", "skill", "accepted", "partner_name", "partner_email", "partner_birth_date", "partner_skill", "partner_accepted"]


@login_required
def roster_import(request, slug):
    event, _ = event_access(request, slug, public=False); require(request.user, event, "operate")
    if request.GET.get("sample"):
        return download(portability.csv_text([CSV_FIELDS, [event.divisions.first().name if event.divisions.exists() else "Division name", "Example team", "Example One", "one@example.invalid", "1990-01-01", "3.0", "", "Example Two", "two@example.invalid", "1990-01-01", "3.0", ""]]), "roster-template.csv", "text/csv; charset=utf-8")
    form = UploadForm(request.POST or None, request.FILES or None)
    preview = None
    session_key = f"roster_preview:{event.id}"
    if request.method == "POST" and request.POST.get("confirm"):
        preview = request.session.get(session_key)
        if not preview or request.POST.get("digest") != services.digest(preview):
            raise DomainError("Upload and review the CSV again before importing.")
        selected = request.POST.getlist("rows")
        if not selected or len(set(selected)) != len(selected) or any(i not in {str(r['line']) for r in preview['rows'] if not r['errors']} for i in selected):
            raise DomainError("Select one or more valid preview rows.")
        selected_rows = [row for row in preview["rows"] if str(row["line"]) in selected]
        @services.command("roster_import", "operate")
        def commit(locked, actor, data):
            for row in data["rows"]:
                services.register(locked.id, actor, {**row["payload"], "policy_version": locked.policy_version, "send_notices": data["send_notices"]}, str(uuid.uuid5(uuid.UUID(data["batch_key"]), str(row["line"]))))
            # Nested registration increments the same event; retain those revisions.
            locked.refresh_from_db()
            return {"count": len(data["rows"])}
        result = commit(event.id, request.user, {"event_revision": preview["revision"], "rows": selected_rows, "send_notices": request.POST.get("send_notices") == "on", "batch_key": preview["key"]}, request.POST.get("operation_key"))
        request.session.pop(session_key, None)
        messages.success(request, f"Imported {result['count']} entries. Invitation delivery follows the choice you confirmed.")
        return redirect(f"/events/{slug}/desk/?tab=entries")
    elif request.method == "POST" and form.is_valid():
        try:
            source = form.cleaned_data["file"].read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(source))
            if reader.fieldnames != CSV_FIELDS:
                raise DomainError("Use the sample CSV headers in their original order.")
            rows, seen = [], set()
            for line, row in enumerate(reader, 2):
                if line > 257:
                    raise DomainError("Import at most 256 entries at a time.")
                if None in row or any(v is None for v in row.values()):
                    raise DomainError(f"Row {line} has the wrong number of columns.")
                division = event.divisions.filter(name=row["division"]).first()
                errors, payload = [], None
                if not division or division.draw_locked:
                    errors.append("Division not found or draw already locked.")
                else:
                    row["accepted"] = row["accepted"].strip().lower() in ("yes", "true", "1")
                    row["partner_accepted"] = row["partner_accepted"].strip().lower() in ("yes", "true", "1")
                    rf = RegistrationForm(row, division=division, assisted=True)
                    if rf.is_valid():
                        payload = rf.payload()
                        for person in payload["people"]:
                            identity = (str(division.id), person["email"].lower())
                            if identity in seen or division.entries.filter(members__participant__email=identity[1], members__active=True).exists():
                                errors.append(f"Duplicate active contact in {division.name}.")
                            seen.add(identity)
                    else:
                        errors.extend(f"{key}: {' '.join(values)}" for key, values in rf.errors.items())
                rows.append({"line": line, "label": row["label"], "errors": errors, "payload": payload})
            if not rows:
                raise DomainError("The CSV contains no entry rows.")
            preview = {"rows": rows, "revision": event.revision, "key": str(uuid.uuid4())}
            request.session[session_key] = preview
        except (UnicodeDecodeError, csv.Error, DomainError) as exc:
            form.add_error(None, str(exc))
    return render(request, "upload.html", {"form": form, "event": event, "title": "Import an assisted roster", "preview": preview, "digest": services.digest(preview) if preview else ""})


@login_required
@require_POST
def reconcile_delivery(request, slug):
    event, _ = event_access(request, slug, public=False)
    operations.reconcile_delivery(event.id, request.user, {**meta(request), "message": request.POST.get("message"), "action": request.POST.get("action"), "reason": request.POST.get("reason", ""), "not_accepted": request.POST.get("not_accepted") == "on"}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=activity")


@login_required
@require_POST
def partial_results(request, slug, division_id):
    event, _ = event_access(request, slug, public=False)
    operations.partial_results(event.id, request.user, {**meta(request), "division": str(division_id), "reason": request.POST.get("reason", "")}, request.POST.get("operation_key"))
    return redirect(f"/events/{slug}/desk/?tab=results")
