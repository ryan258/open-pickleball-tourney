"""Durable claims; ambiguous outcomes never automatically resend."""
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Outbox, Event, Token, RateBucket
from . import services


def maintenance():
    now = timezone.now()
    # A crashed sender may have handed its message to a provider. Preserve uncertainty.
    Outbox.objects.filter(status="sending", attempted_at__lt=now-timedelta(minutes=5)).update(status="uncertain", error="Sender interrupted. Reconcile the stable message ID before any resend.")
    for event_id in Event.objects.filter(status="published").values_list("id", flat=True):
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=event_id)
            before = list(event.divisions.values_list("entries__id", "entries__status", "entries__offer_expires"))
            for division in event.divisions.all():
                services.advance_waitlist(division)
            after = list(event.divisions.values_list("entries__id", "entries__status", "entries__offer_expires"))
            if before != after:
                event.revision += 1; event.save(); services.audit(event, None, "waitlist_maintenance", {})
    # Auth link payloads can include private identity data; expired links need no retention.
    Token.objects.filter(expires_at__lt=now-timedelta(days=7)).delete()
    RateBucket.objects.filter(reset_at__lt=now-timedelta(days=1)).delete()


def deliver_one():
    with transaction.atomic():
        row = Outbox.objects.select_for_update().filter(status="queued", attempts__lt=3).order_by("created_at", "id").first()
        if not row:
            return False
        if row.marketing or (row.event_id and not row.event.external_actions_enabled):
            row.status = "suppressed"; row.error = "Campaign sending or restored-event external actions are disabled."; row.save()
            return True
        row.status = "sending"; row.attempts += 1; row.attempted_at = timezone.now(); row.error = ""; row.save()
    message_id = f"<tourney-{row.id}@open-tourney.local>"
    try:
        sent = EmailMessage(row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [row.recipient], headers={"Message-ID": message_id}).send(fail_silently=False)
        status = "saved_local" if "filebased" in settings.EMAIL_BACKEND or "locmem" in settings.EMAIL_BACKEND else "accepted"
        if sent != 1:
            status = "uncertain"
        error = "" if sent == 1 else "No acceptance evidence. Reconcile before retrying."
    except Exception:
        # Do not persist SMTP credentials, recipient responses or raw exception strings.
        status, error = "uncertain", "Delivery failed or acceptance is unknown. Reconcile the message ID before retrying."
    Outbox.objects.filter(pk=row.pk, status="sending").update(status=status, error=error)
    return True
