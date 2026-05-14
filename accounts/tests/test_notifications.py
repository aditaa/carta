import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import MembershipInvitation
from accounts.notifications import notifications_for_user
from ownership.models import House


def create_user(email: str, *, staff: bool = False, superuser: bool = False):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name=email.split("@")[0].title(),
        is_staff=staff,
        is_superuser=superuser,
    )


@pytest.mark.django_db
def test_superuser_gets_upgrade_notification(monkeypatch):
    superuser = create_user("admin@example.test", staff=True, superuser=True)
    monkeypatch.setattr("accounts.notifications.upgrade_available", lambda: True)

    notifications = notifications_for_user(superuser)

    assert [notification.key for notification in notifications] == ["upgrade_available"]
    assert notifications[0].url == reverse("accounts:application_status")


@pytest.mark.django_db
def test_regular_user_does_not_get_upgrade_notification(monkeypatch):
    user = create_user("denizen@example.test")
    monkeypatch.setattr("accounts.notifications.upgrade_available", lambda: True)

    assert notifications_for_user(user) == []


@pytest.mark.django_db
def test_user_gets_pending_invitation_notification():
    inviter = create_user("admin@example.test", staff=True, superuser=True)
    invitee = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    MembershipInvitation.objects.create(inviter=inviter, invitee=invitee, house=house)

    notifications = notifications_for_user(invitee)

    assert [notification.key for notification in notifications] == ["pending_invitations"]
    assert notifications[0].count == 1
    assert notifications[0].url == reverse("accounts:my_invitations")


@pytest.mark.django_db
def test_pending_invitation_notification_renders_on_page(client, monkeypatch):
    inviter = create_user("admin@example.test", staff=True, superuser=True)
    invitee = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    MembershipInvitation.objects.create(inviter=inviter, invitee=invitee, house=house)
    monkeypatch.setattr("accounts.notifications.upgrade_available", lambda: False)
    client.force_login(invitee)

    response = client.get(reverse("accounts:my_invitations"))

    assert response.status_code == 200
    assert b"Invitations pending" in response.content
    assert b"You have 1 membership invitation waiting." in response.content


@pytest.mark.django_db
def test_upgrade_notification_renders_on_admin_page(client, monkeypatch):
    superuser = create_user("admin@example.test", staff=True, superuser=True)
    monkeypatch.setattr("accounts.notifications.upgrade_available", lambda: True)
    monkeypatch.setattr("accounts.views.upgrade_available", lambda: True)
    client.force_login(superuser)

    response = client.get(reverse("accounts:settings_home"))

    assert response.status_code == 200
    assert b"Upgrade available" in response.content
    assert response.content.index(b"priority-section") < response.content.index(b"settings-grid")
