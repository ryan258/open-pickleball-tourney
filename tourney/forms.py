from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django import forms
from django.conf import settings
from django.utils import timezone
from .models import Event, Division, FORMATS

RELEASED_FORMATS = {"round_robin", "single_elimination"}


def local_instant(value, zone, fold=""):
    try:
        naive = datetime.fromisoformat(value)
        if naive.tzinfo:
            return naive.astimezone(dt_timezone.utc)
        first = naive.replace(tzinfo=zone, fold=0)
        second = naive.replace(tzinfo=zone, fold=1)
        if first.astimezone(dt_timezone.utc).astimezone(zone).replace(tzinfo=None) != naive:
            raise ValueError("This local time does not exist because the clocks change.")
        if first.utcoffset() != second.utcoffset() and fold == "":
            raise ValueError("This time occurs twice. Choose earlier or later under Clock-change times.")
        return naive.replace(tzinfo=zone, fold=int(fold or 0)).astimezone(dt_timezone.utc)
    except (TypeError, ValueError) as exc:
        raise forms.ValidationError(str(exc) or "Enter a valid local date and time.")


class EventForm(forms.ModelForm):
    start_at = forms.CharField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), label="Event starts")
    end_at = forms.CharField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), label="Event ends")
    registration_open = forms.CharField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), label="Registration opens")
    registration_close = forms.CharField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), label="Registration closes")
    fold = forms.ChoiceField(label="Clock-change times", required=False, choices=[("", "Ask if a time is ambiguous"), ("0", "Earlier occurrence"), ("1", "Later occurrence")])
    court_count = forms.IntegerField(min_value=1, max_value=8, initial=4, label="Number of courts")
    visibility = forms.ChoiceField(choices=[("public", "Public — listed in discovery"), ("unlisted", "Unlisted — anyone with the link"), ("private", "Private — invited people only")])
    fee_cents = forms.IntegerField(min_value=0, max_value=1000000, initial=0, label="Entry fee in cents", help_text="0 is free. 2500 is $25. Fees are collected outside this app.")
    rest_minutes = forms.IntegerField(min_value=0, max_value=240, initial=10)
    duration_minutes = forms.IntegerField(min_value=5, max_value=240, initial=25)
    buffer_minutes = forms.IntegerField(min_value=0, max_value=60, initial=5)
    notice = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Participant notice for published changes", help_text="Required when editing an event after publication. Review this text before saving; it will be queued for registered players.")

    class Meta:
        model = Event
        fields = ["title", "summary", "time_zone", "start_at", "end_at", "registration_open", "registration_close",
                  "visibility", "venue", "address", "accessibility", "contact_email", "participation_policy", "refund_policy",
                  "fee_cents", "rest_minutes", "duration_minutes", "buffer_minutes"]
        widgets = {"summary": forms.Textarea(attrs={"rows": 3}), "accessibility": forms.Textarea(attrs={"rows": 3}),
                   "participation_policy": forms.Textarea(attrs={"rows": 3}), "refund_policy": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        zone = ZoneInfo(self.instance.time_zone or "America/Chicago")
        if self.instance.pk and self.instance.start_at:
            for name in ("start_at", "end_at", "registration_open", "registration_close"):
                self.initial[name] = getattr(self.instance, name).astimezone(zone).strftime("%Y-%m-%dT%H:%M")
            self.initial["court_count"] = self.instance.courts.count() or 4
        else:
            start = (timezone.now()+timedelta(days=7)).astimezone(zone).replace(hour=9, minute=0, second=0, microsecond=0)
            for name, value in {"start_at": start, "end_at": start+timedelta(hours=6), "registration_open": timezone.now(), "registration_close": start-timedelta(hours=1)}.items():
                self.initial[name] = value.astimezone(zone).strftime("%Y-%m-%dT%H:%M")
            self.initial["time_zone"] = "America/Chicago"

    def clean(self):
        data = super().clean()
        try:
            zone = ZoneInfo(data.get("time_zone", "America/Chicago"))
        except (ZoneInfoNotFoundError, ValueError):
            self.add_error("time_zone", "Use an IANA zone such as America/Chicago."); return data
        for name in ("start_at", "end_at", "registration_open", "registration_close"):
            if name in data:
                try:
                    data[name] = local_instant(data[name], zone, data.get("fold", ""))
                except forms.ValidationError as exc:
                    self.add_error(name, exc)
        if all(isinstance(data.get(k), datetime) for k in ("start_at", "end_at", "registration_open", "registration_close")):
            if data["end_at"] <= data["start_at"]:
                self.add_error("end_at", "Event end must follow its start.")
            if not data["registration_open"] < data["registration_close"] <= data["end_at"]:
                self.add_error("registration_close", "Registration must close after opening and no later than event end.")
        return data


class DivisionForm(forms.ModelForm):
    capacity = forms.IntegerField(min_value=2, max_value=16, initial=8, help_text="Entries: teams for doubles, people for singles.")
    target = forms.TypedChoiceField(choices=[(11, "11 points"), (15, "15 points"), (21, "21 points")], coerce=int)
    best_of = forms.TypedChoiceField(choices=[(1, "One game"), (3, "Best of three")], coerce=int)
    min_age = forms.IntegerField(min_value=18, max_value=120, initial=18)
    max_age = forms.IntegerField(min_value=18, max_value=120, required=False)
    pool_count = forms.IntegerField(min_value=2, max_value=8, initial=2)
    qualifiers = forms.IntegerField(min_value=1, max_value=8, initial=2)
    class Meta:
        model = Division
        fields = ["name", "discipline", "format", "capacity", "target", "best_of", "skill_min", "skill_max", "min_age", "max_age", "pool_count", "qualifiers", "waitlist_enabled"]
        help_texts = {"skill_min": "Inclusive minimum; leave blank for all skill levels.", "skill_max": "Exclusive maximum. Highest partner rating is used.",
                      "pool_count": "Used only for pools into playoffs.", "qualifiers": "Advancing entries per pool; pool order breaks cross-pool ties."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.ENABLE_EXPERIMENTAL_FORMATS:  # spec: unreleased formats stay disabled; keep an existing division's own format selectable
            self.fields["format"].choices = [c for c in FORMATS if c[0] in RELEASED_FORMATS or c[0] == self.instance.format]
            self.fields["format"].help_text = "Pools and double elimination are not release-gated yet (set ENABLE_EXPERIMENTAL_FORMATS=1 to try them)."

    def clean(self):
        data = super().clean()
        # event is not a form field, so Django skips the (event, name) unique constraint; check it here.
        if data.get("name") and Division.objects.filter(event_id=self.instance.event_id, name=data["name"]).exclude(pk=self.instance.pk).exists():
            self.add_error("name", "This event already has a division with that name.")
        if data.get("skill_min") is not None and data.get("skill_max") is not None and data["skill_min"] >= data["skill_max"]:
            self.add_error("skill_max", "Maximum skill must exceed the minimum.")
        if data.get("max_age") is not None and data.get("min_age") and data["max_age"] < data["min_age"]:
            self.add_error("max_age", "Maximum age must be at least the minimum.")
        return data


class RegistrationForm(forms.Form):
    label = forms.CharField(max_length=120, label="Entry / team display name")
    name = forms.CharField(max_length=100, label="Your display name")
    email = forms.EmailField(label="Your email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    birth_date = forms.DateField(label="Your date of birth (private)", widget=forms.DateInput(attrs={"type": "date"}))
    skill = forms.DecimalField(min_value=1, max_value=8, decimal_places=1, required=False, label="Your self-reported skill")
    partner_name = forms.CharField(max_length=100, required=False)
    partner_email = forms.EmailField(required=False)
    partner_birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Partner date of birth (private)")
    partner_skill = forms.DecimalField(min_value=1, max_value=8, decimal_places=1, required=False)
    accepted = forms.BooleanField(label="I accept the published participation and refund policies and the public display of my entry/results.")
    partner_accepted = forms.BooleanField(required=False, label="As staff, I have separately recorded the partner's explicit acceptance of these policies.")

    def __init__(self, *args, division, assisted=False, **kwargs):
        self.division = division; self.assisted = assisted
        super().__init__(*args, **kwargs)
        if division.discipline == "singles":
            for field in ("partner_name", "partner_email", "partner_birth_date", "partner_skill", "partner_accepted"):
                self.fields.pop(field)
        else:
            for field in ("partner_name", "partner_email", "partner_birth_date"):
                self.fields[field].required = True
        if not assisted:
            self.fields.pop("partner_accepted", None)
        else:
            self.fields["accepted"].label = "I have recorded the first participant's explicit acceptance of the displayed policies."

    def clean(self):
        data = super().clean()
        day = self.division.event.start_at.astimezone(ZoneInfo(self.division.event.time_zone)).date()
        for key in ("birth_date", "partner_birth_date"):
            dob = data.get(key)
            if dob:
                age = day.year-dob.year-((day.month, day.day) < (dob.month, dob.day))
                if age < max(18, self.division.min_age) or (self.division.max_age and age > self.division.max_age):
                    self.add_error(key, "This person is outside the published adult age range.")
        if data.get("partner_email", "").lower() == data.get("email", "").lower():
            self.add_error("partner_email", "Each partner needs a distinct email identity.")
        return data

    def payload(self):
        d = self.cleaned_data
        people = [{"name": d["name"], "email": d["email"].lower(), "birth_date": d["birth_date"].isoformat(),
                   "skill": str(d["skill"]) if d.get("skill") is not None else None, "accepted": d["accepted"]}]
        if self.division.discipline == "doubles":
            people.append({"name": d["partner_name"], "email": d["partner_email"].lower(), "birth_date": d["partner_birth_date"].isoformat(),
                "skill": str(d["partner_skill"]) if d.get("partner_skill") is not None else None, "accepted": d.get("partner_accepted", False)})
        return {"division": str(self.division.id), "label": d["label"], "people": people, "assisted": self.assisted}


class ScoreForm(forms.Form):
    outcome = forms.ChoiceField(choices=[("played", "Played to completion"), ("retirement", "Retirement after play started"),
        ("walkover", "Walkover / no-show before play"), ("disqualification", "Disqualification"), ("void", "Void — no result")])
    game_1_a = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 1 · side A")
    game_1_b = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 1 · side B")
    game_2_a = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 2 · side A")
    game_2_b = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 2 · side B")
    game_3_a = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 3 · side A")
    game_3_b = forms.IntegerField(min_value=0, max_value=999, required=False, label="Game 3 · side B")
    incomplete_a = forms.IntegerField(min_value=0, max_value=999, required=False, label="Incomplete game · side A (retirement / disqualification only)")
    incomplete_b = forms.IntegerField(min_value=0, max_value=999, required=False, label="Incomplete game · side B")
    winner = forms.ChoiceField(choices=[("", "Calculated from played scores"), ("a", "Side A"), ("b", "Side B")], required=False, label="Administrative winner")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, max_length=2000)

    def __init__(self, *args, best_of=1, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(best_of+1, 4):
            self.fields.pop(f"game_{i}_a"); self.fields.pop(f"game_{i}_b")

    def clean(self):
        data = super().clean()
        games, gap = [], False
        for i in range(1, 4):
            a, b = data.get(f"game_{i}_a"), data.get(f"game_{i}_b")
            if a is None and b is None:
                gap = True; continue
            if a is None or b is None or gap:
                raise forms.ValidationError("Enter both scores in order, without skipping a game.")
            games.append([a, b])
        a, b = data.get("incomplete_a"), data.get("incomplete_b")
        if (a is None) != (b is None):
            raise forms.ValidationError("Enter both incomplete game scores, or leave both blank.")
        data["incomplete_game"] = [a, b] if a is not None else None
        data["games"] = games
        return data


class ParticipantForm(forms.Form):
    accommodation = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 3}), label="Private accommodation notes")
    extra_rest_minutes = forms.IntegerField(min_value=0, max_value=240, label="Extra rest minutes", initial=0)
    unavailable = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}), label="Unavailable intervals", help_text="One interval per line: 2026-10-10T12:00 / 2026-10-10T13:00. Times use this event's zone. Include an explicit UTC offset during clock changes.")

    def __init__(self, *args, event, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)

    def clean_unavailable(self):
        intervals = []
        for line in self.cleaned_data["unavailable"].splitlines():
            if not line.strip():
                continue
            parts = line.split(" / ")
            if len(parts) != 2:
                raise forms.ValidationError("Separate the start and end with ' / '.")
            start, end = [local_instant(p.strip(), ZoneInfo(self.event.time_zone)) for p in parts]
            if end <= start:
                raise forms.ValidationError("Every interval must end after it starts.")
            intervals.append({"start": start.isoformat(), "end": end.isoformat()})
        if len(intervals) > 30:
            raise forms.ValidationError("Use at most 30 unavailable intervals.")
        return intervals


class EntryEditForm(forms.Form):
    action = forms.ChoiceField(choices=[("transfer", "Transfer the whole entry"), ("replace", "Replace one participant")])
    division = forms.ModelChoiceField(queryset=Division.objects.none(), required=False, label="Destination division")
    member = forms.ChoiceField(required=False, label="Participant to replace")
    name = forms.CharField(required=False, max_length=100, label="New participant display name")
    email = forms.EmailField(required=False, label="New participant email")
    birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    skill = forms.DecimalField(min_value=1, max_value=8, decimal_places=1, required=False)
    accepted = forms.BooleanField(required=False, label="I separately recorded the replacement participant's explicit acceptance of the displayed event policies.")
    reason = forms.CharField(max_length=300, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, entry, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["division"].queryset = entry.division.event.divisions.filter(draw_locked=False, discipline=entry.division.discipline).exclude(pk=entry.division_id)
        self.fields["member"].choices = [(str(m.id), m.participant.name) for m in entry.members.filter(active=True).select_related("participant")]

    def clean(self):
        data = super().clean()
        required = ("division",) if data.get("action") == "transfer" else ("member", "name", "email", "birth_date")
        for field in required:
            if not data.get(field):
                self.add_error(field, "Required for this action.")
        return data
