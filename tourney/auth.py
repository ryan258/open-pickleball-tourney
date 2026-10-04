import hashlib
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Event, Token, Outbox, Organization, Membership, EventGrant, RateBucket, Participant, Entry
from .engine import DomainError
from .services import issue_token, queue_mail, register, accept_partner


def rate_limit(request, label, limit=10, minutes=15, identity=""):
    key = hashlib.sha256(f"{label}|{request.META.get('REMOTE_ADDR', '')}|{identity}".encode()).hexdigest()
    with transaction.atomic():
        bucket, _ = RateBucket.objects.select_for_update().get_or_create(key=key, defaults={"reset_at": timezone.now()+timedelta(minutes=minutes)})
        if bucket.reset_at <= timezone.now():
            bucket.count = 0; bucket.reset_at = timezone.now()+timedelta(minutes=minutes)
        if bucket.count >= limit:
            raise DomainError("Too many attempts. Wait a few minutes, then try again.", "rate_limited", 429)
        bucket.count += 1; bucket.save()


def login_view(request):
    if request.method == "POST":
        rate_limit(request, "login")
        email = request.POST.get("email", "").lower().strip()
        try:
            validate_email(email)
        except ValidationError:
            return render(request, "login.html", {"error": "Enter a valid email address."})
        exists = get_user_model().objects.filter(email__iexact=email, is_active=True).exists()
        if exists or settings.ALLOW_ORGANIZER_SIGNUP:
            with transaction.atomic():
                raw, token = issue_token("login", email, hours=0.25)
                queue_mail(None, email, "Your Open Tourney sign-in link", f"Open this link, then confirm sign in. It expires in 15 minutes.\n{settings.SITE_URL}/link/{raw}/", f"login:{token.id}")
        return render(request, "login.html", {"sent": True})
    return render(request, "login.html")


def participant_grants(request):
    return {k: v for k, v in request.session.get("participants", {}).items() if v["expires"] > timezone.now().timestamp()}


def grant_participant(request, participant):
    grants = participant_grants(request)
    grants[str(participant.id)] = {"event": str(participant.event_id), "expires": (timezone.now()+timedelta(hours=12)).timestamp()}
    request.session["participants"] = grants


def link_view(request, raw):
    token = Token.objects.filter(digest=hashlib.sha256(raw.encode()).hexdigest(), used_at__isnull=True, expires_at__gt=timezone.now()).select_related("event").first()
    if not token:
        raise DomainError("This link has expired or was already used. Request another link from the sign-in or event page.", "expired", 410)
    if request.method not in ("GET", "POST"):
        raise DomainError("Use GET to review or POST to accept this link.", "method", 405)
    # GET is deliberately non-consuming: mail-preview scanners must not redeem credentials.
    if request.method == "GET":
        return render(request, "link.html", {"token": token, "raw": raw})
    rate_limit(request, "redeem", limit=30)
    with transaction.atomic():
        if token.event_id:
            event = Event.objects.select_for_update().get(pk=token.event_id)
        token = Token.objects.select_for_update().get(pk=token.pk)
        if token.used_at or token.expires_at <= timezone.now():
            raise DomainError("This link is no longer available.", "expired", 410)
        destination = "/dashboard/"
        if token.kind in ("login", "staff"):
            user = get_user_model().objects.filter(email__iexact=token.email).first()
            if user is None:
                if token.kind == "login" and not settings.ALLOW_ORGANIZER_SIGNUP:
                    raise DomainError("Organizer sign-up is currently closed.", "forbidden", 403)
                user = get_user_model().objects.create_user(username=hashlib.sha256(token.email.encode()).hexdigest(), email=token.email)
                user.set_unusable_password(); user.save()
            if not user.is_active:
                raise DomainError("This account is disabled.", "forbidden", 403)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if token.kind == "staff":
                if event.status in ("cancelled", "archived"):
                    raise DomainError("This staff invitation is no longer available.", "expired", 410)
                if token.payload["role"] not in ("director", "desk", "scorer", "promotion", "finance", "viewer"):
                    raise DomainError("Invalid staff grant.")
                EventGrant.objects.update_or_create(event=token.event, user=user, defaults={"role": token.payload["role"]})
                destination = f"/events/{token.event.slug}/desk/"
        elif token.kind == "registration":
            if not request.POST.get("accept"):
                raise DomainError("Accept the displayed participation and refund policies to register.")
            result = register(token.event_id, None, {**token.payload, "policy_version": request.POST.get("policy_version")}, key=token.id)
            entry = Entry.objects.get(pk=result["id"])
            participant = entry.members.get(participant__email=token.email).participant
            grant_participant(request, participant)
            destination = f"/events/{token.event.slug}/my/"
            messages.success(request, f"Your entry is {result['status'].replace('_', ' ')}.")
        elif token.kind == "partner":
            if not request.POST.get("accept"):
                raise DomainError("Accept the policies before joining your partner.")
            accept_partner(token.event_id, None, {**token.payload, "policy_version": request.POST.get("policy_version")}, key=token.id)
            participant = Participant.objects.get(pk=token.payload["participant"], event=token.event)
            grant_participant(request, participant)
            destination = f"/events/{token.event.slug}/my/"
        elif token.kind == "manage":
            participant = Participant.objects.get(pk=token.payload["participant"], event=token.event)
            grant_participant(request, participant)
            destination = f"/events/{token.event.slug}/my/"
        else:
            raise DomainError("This link type is not supported.")
        token.used_at = timezone.now(); token.save()
    return redirect(destination)


@require_POST
def logout_view(request):
    logout(request)
    return redirect("/")


def local_demo_allowed(request):
    from urllib.parse import urlsplit
    return settings.DEMO_MODE and request.META.get("REMOTE_ADDR") in ("127.0.0.1", "::1") and urlsplit("//"+request.get_host()).hostname in ("localhost", "127.0.0.1", "::1")


@require_POST
def demo_login(request):
    if not local_demo_allowed(request):
        raise DomainError("Demo access is only enabled on the local demo server.", "forbidden", 403)
    user = get_user_model().objects.filter(username="local-demo-organizer").first()
    if not user:
        raise DomainError("Run the demo seed command first.")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("/dashboard/")


def mailbox(request):
    if not local_demo_allowed(request):
        raise DomainError("The local mail sink is disabled here.", "not_found", 404)
    return render(request, "mailbox.html", {"letters": Outbox.objects.order_by("-created_at")[:50]})
