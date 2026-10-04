import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True


class Organization(Record):
    name = models.CharField(max_length=120)
    contact_email = models.EmailField()

    def __str__(self):
        return self.name


class Membership(Record):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, default="owner")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "user"], name="one_org_membership")]


class Event(Record):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="events")
    slug = models.SlugField(max_length=150, unique=True)
    title = models.CharField(max_length=150)
    summary = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    time_zone = models.CharField(max_length=64, default="America/Chicago")
    registration_open = models.DateTimeField()
    registration_close = models.DateTimeField()
    visibility = models.CharField(max_length=16, default="public")
    status = models.CharField(max_length=16, default="draft")
    competition = models.CharField(max_length=16, default="setup")
    venue = models.CharField(max_length=160)
    address = models.CharField(max_length=300)
    accessibility = models.TextField(blank=True)
    contact_email = models.EmailField()
    participation_policy = models.TextField(default="Play respectfully, follow the published event rules, and contact the organizer if you need assistance.")
    refund_policy = models.TextField(default="Free event. No payment is required.")
    policy_version = models.PositiveIntegerField(default=1)
    currency = models.CharField(max_length=3, default="USD")
    fee_cents = models.PositiveIntegerField(default=0)
    rest_minutes = models.PositiveIntegerField(default=10)
    duration_minutes = models.PositiveIntegerField(default=25)
    buffer_minutes = models.PositiveIntegerField(default=5)
    revision = models.PositiveIntegerField(default=1)
    hold_reason = models.CharField(max_length=300, blank=True)
    cancellation_reason = models.TextField(blank=True)
    notices = models.JSONField(default=list, blank=True)
    sanction_status = models.CharField(max_length=32, default="not_requested")
    sanction_body = models.CharField(max_length=100, blank=True)
    sanction_reference = models.CharField(max_length=150, blank=True)
    sanction_notes = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False)
    external_actions_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_at", "title"]

    def __str__(self):
        return self.title

    @property
    def registration_is_open(self):
        now = timezone.now()
        return self.status == "published" and self.registration_open <= now < self.registration_close

    @property
    def fee_display(self):
        return "Free" if not self.fee_cents else f"${self.fee_cents / 100:.2f} {self.currency}"


class EventGrant(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="one_event_grant")]


class Court(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="courts")
    name = models.CharField(max_length=80)
    status = models.CharField(max_length=16, default="available")
    notes = models.CharField(max_length=300, blank=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["event", "name"], name="unique_court_name")]


FORMATS = [("round_robin", "Round robin"), ("single_elimination", "Single elimination"),
           ("pools", "Pools into playoffs"), ("double_elimination", "Double elimination")]


class Division(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="divisions")
    name = models.CharField(max_length=100)
    discipline = models.CharField(max_length=10, choices=[("singles", "Singles"), ("doubles", "Doubles")], default="doubles")
    format = models.CharField(max_length=24, choices=FORMATS, default="round_robin")
    capacity = models.PositiveIntegerField(default=8)
    target = models.PositiveIntegerField(default=11)
    best_of = models.PositiveIntegerField(default=1)
    skill_min = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    skill_max = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    min_age = models.PositiveIntegerField(default=18)
    max_age = models.PositiveIntegerField(null=True, blank=True)
    pool_count = models.PositiveIntegerField(default=2)
    qualifiers = models.PositiveIntegerField(default=2)
    waitlist_enabled = models.BooleanField(default=True)
    draw_version = models.PositiveIntegerField(default=0)
    draw_locked = models.BooleanField(default=False)
    rules_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, default="provisional")
    final_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["event", "name"], name="unique_division_name")]

    @property
    def team_size(self):
        return 2 if self.discipline == "doubles" else 1

    @property
    def admitted_count(self):
        return self.entries.filter(status="admitted").count()

    def __str__(self):
        return self.name


class Participant(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    birth_date = models.DateField()
    skill = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    skill_source = models.CharField(max_length=32, default="self_reported")
    accommodation = models.TextField(blank=True)
    extra_rest_minutes = models.PositiveIntegerField(default=0)
    unavailable = models.JSONField(default=list, blank=True)
    marketing_consent = models.BooleanField(default=False)
    marketing_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["event", "email"], condition=~Q(email=""), name="unique_event_email")]


class Entry(Record):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="entries")
    label = models.CharField(max_length=120)
    status = models.CharField(max_length=20, default="incomplete")
    seed = models.PositiveIntegerField(default=0)
    queue_at = models.DateTimeField(default=timezone.now)
    offer_expires = models.DateTimeField(null=True, blank=True)
    offer_paused = models.BooleanField(default=False)
    quoted_fee_cents = models.PositiveIntegerField(default=0)
    quoted_policy = models.JSONField(default=dict)
    pool = models.CharField(max_length=16, blank=True)
    withdrawal_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["seed", "created_at"]

    @property
    def active_members(self):
        return self.members.filter(active=True).select_related("participant")

    @property
    def checked_in(self):
        return self.members.filter(active=True).count() == self.division.team_size and not self.members.filter(active=True, checked_in=False).exists()

    def __str__(self):
        return self.label


class EntryMember(Record):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="members")
    participant = models.ForeignKey(Participant, on_delete=models.PROTECT, related_name="entry_memberships")
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    consent_method = models.CharField(max_length=32, blank=True)
    policy_version = models.PositiveIntegerField(default=1)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entry", "participant"], name="unique_entry_person"),
            models.UniqueConstraint(fields=["division", "participant"], condition=Q(active=True), name="one_active_division_entry"),
        ]


class Draw(Record):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="draws")
    version = models.PositiveIntegerField()
    inputs = models.JSONField()
    digest = models.CharField(max_length=64)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["division", "version"], name="unique_draw_version")]


class Match(Record):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="matches")
    draw_version = models.PositiveIntegerField(default=1)
    number = models.PositiveIntegerField()
    stage = models.CharField(max_length=24, default="round_robin")
    round = models.PositiveIntegerField(default=1)
    pool = models.CharField(max_length=16, blank=True)
    side_a = models.ForeignKey(Entry, on_delete=models.PROTECT, null=True, blank=True, related_name="matches_a")
    side_b = models.ForeignKey(Entry, on_delete=models.PROTECT, null=True, blank=True, related_name="matches_b")
    source_a = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="dependents_a")
    source_b = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="dependents_b")
    source_a_outcome = models.CharField(max_length=8, default="winner")
    source_b_outcome = models.CharField(max_length=8, default="winner")
    status = models.CharField(max_length=24, default="blocked")
    winner = models.ForeignKey(Entry, on_delete=models.PROTECT, null=True, blank=True, related_name="won_matches")
    outcome = models.CharField(max_length=24, blank=True)
    court = models.ForeignKey(Court, on_delete=models.PROTECT, null=True, blank=True, related_name="matches")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    pinned = models.BooleanField(default=False)
    called_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    incident = models.TextField(blank=True)
    assigned_scorer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_matches")

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["division", "draw_version", "number"], name="unique_match_number")]

    @property
    def code(self):
        return f"M-{str(self.division_id)[:4].upper()}-{self.number:03}"

    @property
    def current_result(self):
        return self.results.filter(status="confirmed").first()

    @property
    def label(self):
        return f"{self.side_a.label if self.side_a else 'Awaiting entry'} vs {self.side_b.label if self.side_b else 'Awaiting entry'}"


class Result(Record):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="results")
    revision = models.PositiveIntegerField()
    status = models.CharField(max_length=16, default="submitted")
    games = models.JSONField(default=list)
    incomplete_game = models.JSONField(null=True, blank=True)
    outcome = models.CharField(max_length=24, default="played")
    winner = models.ForeignKey(Entry, on_delete=models.PROTECT, null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="submitted_results")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="confirmed_results")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["match", "revision"], name="unique_result_revision"),
            models.UniqueConstraint(fields=["match"], condition=Q(status="confirmed"), name="one_confirmed_result"),
        ]


class Audit(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="audit")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=80)
    detail = models.JSONField(default=dict)
    event_revision = models.PositiveIntegerField()
    class Meta:
        ordering = ["-created_at"]


class Operation(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    key = models.UUIDField()
    actor_key = models.CharField(max_length=150)
    action = models.CharField(max_length=80)
    digest = models.CharField(max_length=64)
    result = models.JSONField(default=dict)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "key"], name="unique_event_operation")]


class Token(Record):
    digest = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=24)
    email = models.EmailField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    payload = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class Outbox(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name="outbox")
    key = models.CharField(max_length=200, unique=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=24, default="queued")
    attempts = models.PositiveIntegerField(default=0)
    attempted_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)
    marketing = models.BooleanField(default=False)


class Receipt(Record):
    entry = models.ForeignKey(Entry, on_delete=models.PROTECT, related_name="receipts")
    kind = models.CharField(max_length=16, default="payment")
    amount_cents = models.PositiveIntegerField()
    reference = models.CharField(max_length=150)
    method = models.CharField(max_length=50, default="External payment")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)


class Package(Record):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="packages")
    kind = models.CharField(max_length=30, default="generic_results")
    event_revision = models.PositiveIntegerField()
    digest = models.CharField(max_length=64)
    payload = models.JSONField()
    status = models.CharField(max_length=24, default="generated")
    notes = models.TextField(blank=True)


class RateBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    reset_at = models.DateTimeField()

