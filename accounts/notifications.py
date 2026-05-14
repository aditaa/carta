from dataclasses import dataclass

from django.db import DatabaseError, ProgrammingError
from django.urls import reverse

from accounts.models import MembershipInvitation
from accounts.services import upgrade_available


@dataclass(frozen=True)
class InAppNotification:
    key: str
    level: str
    title: str
    message: str
    url: str
    action_label: str
    count: int = 1


def notifications_for_user(user) -> list[InAppNotification]:
    if not getattr(user, "is_authenticated", False):
        return []

    notifications = []
    notifications.extend(_upgrade_notifications(user))
    notifications.extend(_invitation_notifications(user))
    return notifications


def _upgrade_notifications(user) -> list[InAppNotification]:
    if not getattr(user, "is_superuser", False):
        return []
    try:
        has_upgrade = upgrade_available()
    except (DatabaseError, ProgrammingError, RuntimeError, OSError):
        return []
    if not has_upgrade:
        return []
    return [
        InAppNotification(
            key="upgrade_available",
            level="warning",
            title="Upgrade available",
            message="A newer release is available for this Carta Arcanum installation.",
            url=reverse("accounts:application_status"),
            action_label="Open upgrade",
        )
    ]


def _invitation_notifications(user) -> list[InAppNotification]:
    try:
        pending_count = MembershipInvitation.objects.filter(
            invitee=user,
            status=MembershipInvitation.Status.PENDING,
        ).count()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return []
    if pending_count < 1:
        return []

    invitation_label = "invitation" if pending_count == 1 else "invitations"
    return [
        InAppNotification(
            key="pending_invitations",
            level="info",
            title="Invitations pending",
            message=f"You have {pending_count} membership {invitation_label} waiting.",
            url=reverse("accounts:my_invitations"),
            action_label="Review invitations",
            count=pending_count,
        )
    ]
