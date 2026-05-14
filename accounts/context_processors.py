from django.db import DatabaseError, ProgrammingError
from django.urls import reverse

from accounts.bug_reports import CRASH_REPORT_SESSION_KEY
from accounts.notifications import InAppNotification, notifications_for_user
from accounts.services import application_setting_map
from ownership.models import HouseMembership, KingdomMembership


def application_settings(request):
    try:
        settings_map = application_setting_map()
    except (DatabaseError, ProgrammingError, RuntimeError):
        settings_map = {}
    notifications = notifications_for_user(getattr(request, "user", None))
    crash_notification = _crash_notification(request)
    if crash_notification:
        notifications = [crash_notification, *notifications]
    return {
        "application_site_name": settings_map.get("site_name", "Carta Arcanum"),
        "application_maintenance_notice": settings_map.get("maintenance_notice", ""),
        "in_app_notifications": notifications,
        "in_app_notification_count": sum(notification.count for notification in notifications),
        "show_house_admin_nav": _has_house_admin(request),
        "show_kingdom_admin_nav": _has_kingdom_admin(request),
    }


def _has_house_admin(request) -> bool:
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    try:
        return HouseMembership.objects.filter(user=user, active=True, role="admin").exists()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return False


def _crash_notification(request) -> InAppNotification | None:
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return None
    session = getattr(request, "session", None)
    if not session or not session.get(CRASH_REPORT_SESSION_KEY):
        return None
    return InAppNotification(
        key="recent_crash",
        level="warning",
        title="Recent crash detected",
        message="Carta Arcanum saved safe crash details for a bug report.",
        url=reverse("accounts:report_bug"),
        action_label="Report crash",
    )


def _has_kingdom_admin(request) -> bool:
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    try:
        return KingdomMembership.objects.filter(user=user, active=True, role="admin").exists()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return False
