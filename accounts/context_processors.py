from django.db import DatabaseError, ProgrammingError

from accounts.notifications import notifications_for_user
from accounts.services import application_setting_map
from ownership.models import HouseMembership, KingdomMembership


def application_settings(request):
    try:
        settings_map = application_setting_map()
    except (DatabaseError, ProgrammingError, RuntimeError):
        settings_map = {}
    notifications = notifications_for_user(getattr(request, "user", None))
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
