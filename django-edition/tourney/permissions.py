from .models import Membership, EventGrant
from .engine import DomainError

ROLES = {
    "owner": {"view", "edit", "operate", "score", "correct", "finalize", "promote", "finance", "export", "staff", "evidence"},
    "director": {"view", "edit", "operate", "score", "correct", "finalize", "promote", "finance", "export", "staff", "evidence"},
    "desk": {"view", "operate", "score"},
    "scorer": {"score"},
    "promotion": {"promote"},
    "finance": {"finance"},
    "viewer": set(),
}


def role_for(user, event):
    if not user or not user.is_authenticated or not user.is_active:
        return ""
    if Membership.objects.filter(organization=event.organization, user=user, role="owner").exists():
        return "owner"
    return EventGrant.objects.filter(event=event, user=user).values_list("role", flat=True).first() or ""


def capabilities(user, event):
    return ROLES.get(role_for(user, event), set())


def require(user, event, capability):
    if capability not in capabilities(user, event):
        raise DomainError("You do not have access to this action.", "forbidden", 403)


def require_match(user, event, match):
    require(user, event, "score")
    if role_for(user, event) == "scorer" and match.assigned_scorer_id != user.pk:
        raise DomainError("This match is not assigned to you.", "forbidden", 403)


def require_owner(user, event):
    if role_for(user, event) != "owner":
        raise DomainError("Only the organization owner can do this.", "forbidden", 403)
