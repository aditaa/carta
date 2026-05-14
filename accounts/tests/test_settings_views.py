import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from accounts.models import ApplicationSetting, AuditLogEntry, DenizenProfile, MembershipInvitation
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, Role


@pytest.fixture(autouse=True)
def installed_app(settings, tmp_path):
    settings.INSTALLER_LOCK_FILE = tmp_path / "installer.lock"
    settings.INSTALLER_LOCK_FILE.write_text("installed\n", encoding="utf-8")


def create_user(email: str, *, staff: bool = False, superuser: bool = False):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name=email.split("@")[0].title(),
        is_staff=staff,
        is_superuser=superuser,
    )


@pytest.mark.django_db
def test_settings_home_requires_staff(client):
    user = create_user("denizen@example.test")
    client.force_login(user)

    response = client.get(reverse("accounts:settings_home"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_settings_home_shows_status_counts(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    HouseMembership.objects.create(user=staff, house=house, role=Role.ADMIN)
    KingdomMembership.objects.create(user=staff, kingdom=kingdom, role=Role.ADMIN)
    client.force_login(staff)

    response = client.get(reverse("accounts:settings_home"))

    assert response.status_code == 200
    assert b"Settings" in response.content
    assert b"Manage user access" in response.content
    assert b"House ACL" in response.content
    assert b"Kingdom ACL" in response.content
    assert b"View status" in response.content


@pytest.mark.django_db
def test_application_status_shows_health_checks_and_settings(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)

    response = client.get(reverse("accounts:application_status"))

    assert response.status_code == 200
    assert b"Application Status" in response.content
    assert b"Health Checks" in response.content
    assert b"Site name" in response.content
    assert b"Maintenance notice" in response.content
    assert b"Email backend" in response.content
    assert b"Upgrade" in response.content


@pytest.mark.django_db
def test_application_status_uses_release_branch_dropdown(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)

    response = client.get(reverse("accounts:application_status"))

    assert response.status_code == 200
    assert b"<select" in response.content
    assert b'<option value="stable" selected>Stable</option>' in response.content
    assert b'<option value="main">Testing</option>' in response.content
    assert b"Stable tracks the stable branch. Testing tracks main." in response.content


@pytest.mark.django_db
def test_superuser_can_send_test_email(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    client.get(reverse("accounts:application_status"))
    ApplicationSetting.objects.filter(key="email_backend").update(
        value="django.core.mail.backends.locmem.EmailBackend"
    )

    response = client.post(
        reverse("accounts:send_test_email"),
        {"recipient": "admin@example.test"},
    )

    assert response.status_code == 302
    assert AuditLogEntry.objects.filter(action="test_email_sent").exists()


@pytest.mark.django_db
def test_application_status_updates_editable_settings(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    client.get(reverse("accounts:application_status"))
    settings_rows = list(ApplicationSetting.objects.order_by("id"))

    post_data = {
        "form-TOTAL_FORMS": str(len(settings_rows)),
        "form-INITIAL_FORMS": str(len(settings_rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, setting in enumerate(settings_rows):
        post_data[f"form-{index}-id"] = str(setting.id)
        post_data[f"form-{index}-value"] = (
            "Carta Test" if setting.key == "site_name" else setting.value
        )

    response = client.post(reverse("accounts:application_status"), post_data)

    assert response.status_code == 302
    assert ApplicationSetting.objects.get(key="site_name").value == "Carta Test"
    assert AuditLogEntry.objects.filter(action="application_settings_updated").exists()


@pytest.mark.django_db
def test_application_status_rejects_invalid_email_settings(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    client.get(reverse("accounts:application_status"))
    settings_rows = list(ApplicationSetting.objects.order_by("id"))

    post_data = {
        "form-TOTAL_FORMS": str(len(settings_rows)),
        "form-INITIAL_FORMS": str(len(settings_rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, setting in enumerate(settings_rows):
        post_data[f"form-{index}-id"] = str(setting.id)
        if setting.key == "email_backend":
            value = "django.core.mail.backends.smtp.EmailBackend"
        elif setting.key == "email_port":
            value = "not-a-port"
        elif setting.key == "email_use_tls":
            value = "true"
        elif setting.key == "email_use_ssl":
            value = "true"
        elif setting.key == "email_host":
            value = ""
        elif setting.key == "email_from_address":
            value = ""
        else:
            value = setting.value
        post_data[f"form-{index}-value"] = value

    response = client.post(reverse("accounts:application_status"), post_data)

    assert response.status_code == 200
    assert b"Email port must be a number from 1 to 65535" in response.content
    assert b"Email TLS and SSL cannot both be enabled" in response.content
    assert ApplicationSetting.objects.get(key="email_port").value != "not-a-port"


@pytest.mark.django_db
def test_application_status_rejects_invalid_release_branch(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    client.get(reverse("accounts:application_status"))
    settings_rows = list(ApplicationSetting.objects.order_by("id"))

    post_data = {
        "form-TOTAL_FORMS": str(len(settings_rows)),
        "form-INITIAL_FORMS": str(len(settings_rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, setting in enumerate(settings_rows):
        post_data[f"form-{index}-id"] = str(setting.id)
        post_data[f"form-{index}-value"] = (
            "feature branch" if setting.key == "release_branch" else setting.value
        )

    response = client.post(reverse("accounts:application_status"), post_data)

    assert response.status_code == 200
    assert b"Release branch can only contain" in response.content
    assert ApplicationSetting.objects.get(key="release_branch").value == "stable"


@pytest.mark.django_db
def test_application_status_can_select_testing_release_branch(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    client.get(reverse("accounts:application_status"))
    settings_rows = list(ApplicationSetting.objects.order_by("id"))

    post_data = {
        "form-TOTAL_FORMS": str(len(settings_rows)),
        "form-INITIAL_FORMS": str(len(settings_rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, setting in enumerate(settings_rows):
        post_data[f"form-{index}-id"] = str(setting.id)
        post_data[f"form-{index}-value"] = (
            "main" if setting.key == "release_branch" else setting.value
        )

    response = client.post(reverse("accounts:application_status"), post_data)

    assert response.status_code == 302
    assert ApplicationSetting.objects.get(key="release_branch").value == "main"


@pytest.mark.django_db
def test_start_upgrade_redirects_to_status_page(client, monkeypatch):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    monkeypatch.setattr("accounts.views.start_upgrade_job", lambda: "job-123")

    response = client.post(reverse("accounts:start_upgrade"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:upgrade_status", args=["job-123"])


@pytest.mark.django_db
def test_upgrade_status_json_reports_job(client, monkeypatch):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    monkeypatch.setattr(
        "accounts.views.upgrade_job_status",
        lambda job_id: {
            "status": "complete",
            "message": f"{job_id} done",
            "output": "",
            "error": "",
        },
    )

    response = client.get(reverse("accounts:upgrade_status_json", args=["job-123"]))

    assert response.status_code == 200
    assert response.json()["message"] == "job-123 done"


@pytest.mark.django_db
def test_upgrade_status_renders_expandable_output(client, monkeypatch):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    monkeypatch.setattr(
        "accounts.views.upgrade_job_status",
        lambda job_id: {
            "status": "running",
            "message": "Running database migrations",
            "output": "$ python manage.py migrate --noinput\nApplying accounts.0001_initial...",
            "error": "",
        },
    )

    response = client.get(reverse("accounts:upgrade_status", args=["job-123"]))

    assert response.status_code == 200
    assert b"<details" in response.content
    assert b"Upgrade details" in response.content
    assert b"Applying accounts.0001_initial" in response.content


@pytest.mark.django_db
def test_restore_git_file_logs_audit_entry(client, monkeypatch):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)
    restored = []
    monkeypatch.setattr("accounts.views.restore_git_file", lambda path: restored.append(path))

    response = client.post(reverse("accounts:fix_git_file"), {"path": "accounts/models.py"})

    assert response.status_code == 302
    assert restored == ["accounts/models.py"]
    assert AuditLogEntry.objects.filter(action="git_file_restored").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_name", "method", "args", "data"),
    [
        ("accounts:settings_home", "get", (), {}),
        ("accounts:application_status", "get", (), {}),
        ("accounts:application_status", "post", (), {}),
        ("accounts:send_test_email", "post", (), {"recipient": "denizen@example.test"}),
        ("accounts:fix_git_file", "post", (), {"path": "accounts/models.py"}),
        ("accounts:reset_git_files", "post", (), {}),
        ("accounts:start_upgrade", "post", (), {}),
        ("accounts:upgrade_status", "get", ("job-123",), {}),
        ("accounts:upgrade_status_json", "get", ("job-123",), {}),
        ("accounts:audit_log", "get", (), {}),
    ],
)
def test_superuser_status_routes_reject_standard_users(client, route_name, method, args, data):
    user = create_user("denizen@example.test")
    client.force_login(user)

    response = getattr(client, method)(reverse(route_name, args=args), data)

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_audit_detail_rejects_standard_users(client):
    user = create_user("denizen@example.test")
    entry = AuditLogEntry.objects.create(
        actor=user,
        action="test_action",
        target_type="User",
        target_id=str(user.id),
        target_label=str(user),
    )
    client.force_login(user)

    response = client.get(reverse("accounts:audit_log_detail", args=[entry.id]))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_user_access_list_shows_acl_summary(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=target, house=house, role=Role.MEMBER)
    client.force_login(staff)

    response = client.get(reverse("accounts:user_access_list"))

    assert response.status_code == 200
    assert b"denizen@example.test" in response.content
    assert b"1 house" in response.content
    assert b"0 kingdom" in response.content


@pytest.mark.django_db
def test_user_access_list_is_paginated_for_large_admin_view(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    for index in range(55):
        create_user(f"user-{index}@example.test")
    client.force_login(staff)

    response = client.get(reverse("accounts:user_access_list"))

    assert response.status_code == 200
    assert b"Page 1 of 2" in response.content


@pytest.mark.django_db
def test_house_admin_only_sees_house_users(client):
    house_admin = create_user("house-admin@example.test")
    housemate = create_user("housemate@example.test")
    create_user("outsider@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    HouseMembership.objects.create(user=housemate, house=house, role=Role.MEMBER)
    client.force_login(house_admin)

    response = client.get(reverse("accounts:user_access_list"))

    assert response.status_code == 200
    assert b"housemate@example.test" in response.content
    assert b"outsider@example.test" not in response.content


@pytest.mark.django_db
def test_house_admin_cannot_create_user_with_platform_permissions(client):
    house_admin = create_user("house-admin@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    permission = Permission.objects.get(codename="add_group")
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:user_create"),
        {
            "email": "new@example.test",
            "display_name": "New Denizen",
            "password1": "swordfish-12345",
            "password2": "swordfish-12345",
            "is_active": "on",
            "is_staff": "on",
            "user_permissions": [str(permission.id)],
        },
    )

    assert response.status_code == 200
    assert b"Only superusers can grant platform permissions" in response.content
    assert not get_user_model().objects.filter(email="new@example.test").exists()


@pytest.mark.django_db
def test_staff_can_create_user_with_initial_permissions(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    permission = Permission.objects.get(codename="add_group")
    client.force_login(staff)

    response = client.post(
        reverse("accounts:user_create"),
        {
            "email": "new@example.test",
            "display_name": "New Denizen",
            "password1": "swordfish",
            "password2": "swordfish",
            "is_active": "on",
            "is_staff": "on",
            "user_permissions": [str(permission.id)],
        },
    )

    user = get_user_model().objects.get(email="new@example.test")
    assert response.status_code == 302
    assert response.url == reverse("accounts:user_access_detail", args=[user.id])
    assert user.display_name == "New Denizen"
    assert user.is_active
    assert user.is_staff
    assert user.has_perm("auth.add_group")
    assert user.denizen_profile
    assert AuditLogEntry.objects.filter(action="user_created", target_id=str(user.id)).exists()


@pytest.mark.django_db
def test_user_access_detail_updates_platform_and_ownership_acl(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    permission = Permission.objects.get(codename="add_group")
    client.force_login(staff)

    response = client.post(
        reverse("accounts:user_access_detail", args=[target.id]),
        {
            "email": "denizen@example.test",
            "display_name": "Updated Denizen",
            "is_active": "on",
            "user_permissions": [str(permission.id)],
            "character_name": "Aster",
            "status": DenizenProfile.Status.ACTIVE,
            "houses-TOTAL_FORMS": "1",
            "houses-INITIAL_FORMS": "0",
            "houses-MIN_NUM_FORMS": "0",
            "houses-MAX_NUM_FORMS": "1000",
            "houses-0-house": str(house.id),
            "houses-0-role": Role.MANAGER,
            "houses-0-active": "on",
            "kingdoms-TOTAL_FORMS": "1",
            "kingdoms-INITIAL_FORMS": "0",
            "kingdoms-MIN_NUM_FORMS": "0",
            "kingdoms-MAX_NUM_FORMS": "1000",
            "kingdoms-0-kingdom": str(kingdom.id),
            "kingdoms-0-role": Role.READ_ONLY,
            "kingdoms-0-active": "on",
        },
    )

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.display_name == "Updated Denizen"
    assert target.has_perm("auth.add_group")
    assert target.house_memberships.get(house=house).role == Role.MANAGER
    assert target.kingdom_memberships.get(kingdom=kingdom).role == Role.READ_ONLY
    assert target.denizen_profile.character_name == "Aster"


@pytest.mark.django_db
def test_staff_cannot_remove_own_staff_access_from_settings(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)

    response = client.post(
        reverse("accounts:user_access_detail", args=[staff.id]),
        {
            "email": "admin@example.test",
            "display_name": "Admin",
            "is_active": "on",
            "status": DenizenProfile.Status.ACTIVE,
            "houses-TOTAL_FORMS": "0",
            "houses-INITIAL_FORMS": "0",
            "houses-MIN_NUM_FORMS": "0",
            "houses-MAX_NUM_FORMS": "1000",
            "kingdoms-TOTAL_FORMS": "0",
            "kingdoms-INITIAL_FORMS": "0",
            "kingdoms-MIN_NUM_FORMS": "0",
            "kingdoms-MAX_NUM_FORMS": "1000",
        },
    )

    assert response.status_code == 200
    assert b"You cannot remove your own settings access" in response.content
    staff.refresh_from_db()
    assert staff.is_staff


@pytest.mark.django_db
def test_house_admin_cannot_grant_platform_permissions_on_user_update(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    membership = HouseMembership.objects.create(user=target, house=house, role=Role.MEMBER)
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    permission = Permission.objects.get(codename="add_group")
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:user_access_detail", args=[target.id]),
        {
            "email": "denizen@example.test",
            "display_name": "Denizen",
            "is_active": "on",
            "is_staff": "on",
            "is_superuser": "on",
            "user_permissions": [str(permission.id)],
            "character_name": "",
            "status": DenizenProfile.Status.ACTIVE,
            "houses-TOTAL_FORMS": "1",
            "houses-INITIAL_FORMS": "1",
            "houses-MIN_NUM_FORMS": "0",
            "houses-MAX_NUM_FORMS": "1000",
            "houses-0-id": str(membership.id),
            "houses-0-house": str(house.id),
            "houses-0-role": Role.MEMBER,
            "houses-0-active": "on",
            "kingdoms-TOTAL_FORMS": "0",
            "kingdoms-INITIAL_FORMS": "0",
            "kingdoms-MIN_NUM_FORMS": "0",
            "kingdoms-MAX_NUM_FORMS": "1000",
        },
    )

    assert response.status_code == 200
    assert b"Only superusers can grant platform permissions" in response.content
    target.refresh_from_db()
    assert not target.is_staff
    assert not target.is_superuser
    assert not target.has_perm("auth.add_group")


@pytest.mark.django_db
def test_staff_can_disable_user(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=target, house=house, role=Role.MEMBER)
    client.force_login(staff)

    response = client.post(reverse("accounts:user_delete", args=[target.id]))

    assert response.status_code == 302
    assert response.url == reverse("accounts:user_access_list")
    target.refresh_from_db()
    assert not target.is_active
    assert AuditLogEntry.objects.filter(action="user_disabled", target_id=str(target.id)).exists()


@pytest.mark.django_db
def test_house_admin_can_reenable_disabled_house_user(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    target.is_active = False
    target.save(update_fields=["is_active"])
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    HouseMembership.objects.create(user=target, house=house, role=Role.MEMBER)
    client.force_login(house_admin)

    response = client.post(reverse("accounts:user_enable", args=[target.id]))

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.is_active
    assert AuditLogEntry.objects.filter(action="user_enabled", target_id=str(target.id)).exists()


@pytest.mark.django_db
def test_house_admin_can_remove_house_membership(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    membership = HouseMembership.objects.create(user=target, house=house, role=Role.MEMBER)
    client.force_login(house_admin)

    response = client.post(reverse("accounts:remove_house_membership", args=[membership.id]))

    assert response.status_code == 302
    membership.refresh_from_db()
    assert not membership.active
    assert AuditLogEntry.objects.filter(action="house_membership_removed").exists()


@pytest.mark.django_db
def test_house_admin_cannot_remove_membership_from_other_house(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    managed_house = House.objects.create(key="bramble", name="House Bramble")
    other_house = House.objects.create(key="ember", name="House Ember")
    HouseMembership.objects.create(user=house_admin, house=managed_house, role=Role.ADMIN)
    membership = HouseMembership.objects.create(user=target, house=other_house, role=Role.MEMBER)
    client.force_login(house_admin)

    response = client.post(reverse("accounts:remove_house_membership", args=[membership.id]))

    assert response.status_code == 302
    assert response.url == reverse("accounts:user_access_list")
    membership.refresh_from_db()
    assert membership.active
    assert not AuditLogEntry.objects.filter(action="house_membership_removed").exists()


@pytest.mark.django_db
def test_kingdom_admin_cannot_remove_membership_from_other_kingdom(client):
    kingdom_admin = create_user("kingdom-admin@example.test")
    target = create_user("denizen@example.test")
    managed_kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    other_kingdom = Kingdom.objects.create(key="morrow", name="Morrow")
    KingdomMembership.objects.create(user=kingdom_admin, kingdom=managed_kingdom, role=Role.ADMIN)
    membership = KingdomMembership.objects.create(
        user=target,
        kingdom=other_kingdom,
        role=Role.MEMBER,
    )
    client.force_login(kingdom_admin)

    response = client.post(reverse("accounts:remove_kingdom_membership", args=[membership.id]))

    assert response.status_code == 302
    assert response.url == reverse("accounts:user_access_list")
    membership.refresh_from_db()
    assert membership.active
    assert not AuditLogEntry.objects.filter(action="kingdom_membership_removed").exists()


@pytest.mark.django_db
def test_house_admin_can_invite_user_and_user_accepts_in_app(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:invite_user"),
        {
            "invitee": str(target.id),
            "target_type": "house",
            "house": str(house.id),
            "role": Role.MEMBER,
        },
    )

    assert response.status_code == 302
    invitation = MembershipInvitation.objects.get(invitee=target, house=house)
    assert invitation.status == MembershipInvitation.Status.PENDING

    client.force_login(target)
    response = client.post(
        reverse("accounts:respond_to_invitation", args=[invitation.id]),
        {"response": "accept"},
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.status == MembershipInvitation.Status.ACCEPTED
    assert HouseMembership.objects.filter(user=target, house=house, active=True).exists()


@pytest.mark.django_db
def test_user_cannot_respond_to_another_users_invitation(client):
    inviter = create_user("admin@example.test", staff=True, superuser=True)
    invitee = create_user("invitee@example.test")
    other_user = create_user("other@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    invitation = MembershipInvitation.objects.create(inviter=inviter, invitee=invitee, house=house)
    client.force_login(other_user)

    response = client.post(
        reverse("accounts:respond_to_invitation", args=[invitation.id]),
        {"response": "accept"},
    )

    assert response.status_code == 404
    invitation.refresh_from_db()
    assert invitation.status == MembershipInvitation.Status.PENDING
    assert not HouseMembership.objects.filter(user=other_user, house=house).exists()


@pytest.mark.django_db
def test_user_cannot_accept_stale_house_invite_after_joining_another_house(client):
    inviter = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    invited_house = House.objects.create(key="bramble", name="House Bramble")
    other_house = House.objects.create(key="ember", name="House Ember")
    invitation = MembershipInvitation.objects.create(
        inviter=inviter,
        invitee=target,
        house=invited_house,
    )
    HouseMembership.objects.create(user=target, house=other_house, role=Role.MEMBER)
    client.force_login(target)

    response = client.post(
        reverse("accounts:respond_to_invitation", args=[invitation.id]),
        {"response": "accept"},
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.status == MembershipInvitation.Status.PENDING
    assert not HouseMembership.objects.filter(user=target, house=invited_house).exists()


@pytest.mark.django_db
def test_user_cannot_accept_stale_kingdom_invite_after_joining_another_kingdom(client):
    inviter = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    invited_kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    other_kingdom = Kingdom.objects.create(key="morrow", name="Morrow")
    invitation = MembershipInvitation.objects.create(
        inviter=inviter,
        invitee=target,
        kingdom=invited_kingdom,
    )
    KingdomMembership.objects.create(user=target, kingdom=other_kingdom, role=Role.MEMBER)
    client.force_login(target)

    response = client.post(
        reverse("accounts:respond_to_invitation", args=[invitation.id]),
        {"response": "accept"},
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.status == MembershipInvitation.Status.PENDING
    assert not KingdomMembership.objects.filter(user=target, kingdom=invited_kingdom).exists()


@pytest.mark.django_db
def test_house_admin_pages_are_scoped_to_admin_houses(client):
    house_admin = create_user("house-admin@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    hidden_house = House.objects.create(key="ember", name="House Ember")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    client.force_login(house_admin)

    response = client.get(reverse("accounts:house_admin_list"))

    assert response.status_code == 200
    assert b"House Bramble" in response.content
    assert b"House Ember" not in response.content

    response = client.get(reverse("accounts:house_admin_detail", args=[hidden_house.id]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_house_admin_cannot_post_to_unmanaged_house(client):
    house_admin = create_user("house-admin@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    hidden_house = House.objects.create(key="ember", name="House Ember")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:house_admin_detail", args=[hidden_house.id]),
        {"key": "ember", "name": "Compromised", "description": ""},
    )

    assert response.status_code == 404
    hidden_house.refresh_from_db()
    assert hidden_house.name == "House Ember"


@pytest.mark.django_db
def test_kingdom_admin_can_update_kingdom(client):
    kingdom_admin = create_user("kingdom-admin@example.test")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    KingdomMembership.objects.create(user=kingdom_admin, kingdom=kingdom, role=Role.ADMIN)
    client.force_login(kingdom_admin)

    response = client.post(
        reverse("accounts:kingdom_admin_detail", args=[kingdom.id]),
        {"key": "valrann", "name": "ValRann Updated", "description": "Notes"},
    )

    assert response.status_code == 302
    kingdom.refresh_from_db()
    assert kingdom.name == "ValRann Updated"
    assert AuditLogEntry.objects.filter(action="kingdom_updated").exists()


@pytest.mark.django_db
def test_kingdom_admin_pages_are_scoped_to_admin_kingdoms(client):
    kingdom_admin = create_user("kingdom-admin@example.test")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    hidden_kingdom = Kingdom.objects.create(key="morrow", name="Morrow")
    KingdomMembership.objects.create(user=kingdom_admin, kingdom=kingdom, role=Role.ADMIN)
    client.force_login(kingdom_admin)

    response = client.get(reverse("accounts:kingdom_admin_list"))

    assert response.status_code == 200
    assert b"ValRann" in response.content
    assert b"Morrow" not in response.content

    response = client.post(
        reverse("accounts:kingdom_admin_detail", args=[hidden_kingdom.id]),
        {"key": "morrow", "name": "Compromised", "description": ""},
    )
    assert response.status_code == 404
    hidden_kingdom.refresh_from_db()
    assert hidden_kingdom.name == "Morrow"


@pytest.mark.django_db
def test_duplicate_pending_house_invite_is_rejected(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    MembershipInvitation.objects.create(inviter=house_admin, invitee=target, house=house)
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:invite_user"),
        {
            "invitee": str(target.id),
            "target_type": "house",
            "house": str(house.id),
            "role": Role.MEMBER,
        },
    )

    assert response.status_code == 200
    assert b"pending house invitation" in response.content
    assert MembershipInvitation.objects.filter(invitee=target, house=house).count() == 1


@pytest.mark.django_db
def test_house_invite_is_rejected_when_user_already_has_house(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    other_house = House.objects.create(key="ember", name="House Ember")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    HouseMembership.objects.create(user=target, house=other_house, role=Role.MEMBER)
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:invite_user"),
        {
            "invitee": str(target.id),
            "target_type": "house",
            "house": str(house.id),
            "role": Role.MEMBER,
        },
    )

    assert response.status_code == 200
    assert b"already belongs to a house" in response.content


@pytest.mark.django_db
def test_house_admin_cannot_invite_user_to_unmanaged_house(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    managed_house = House.objects.create(key="bramble", name="House Bramble")
    hidden_house = House.objects.create(key="ember", name="House Ember")
    HouseMembership.objects.create(user=house_admin, house=managed_house, role=Role.ADMIN)
    client.force_login(house_admin)

    response = client.post(
        reverse("accounts:invite_user"),
        {
            "invitee": str(target.id),
            "target_type": "house",
            "house": str(hidden_house.id),
            "role": Role.MEMBER,
        },
    )

    assert response.status_code == 200
    assert b"Select a valid choice" in response.content
    assert not MembershipInvitation.objects.filter(invitee=target, house=hidden_house).exists()


@pytest.mark.django_db
def test_house_admin_can_cancel_pending_invite(client):
    house_admin = create_user("house-admin@example.test")
    target = create_user("denizen@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=house_admin, house=house, role=Role.ADMIN)
    invitation = MembershipInvitation.objects.create(
        inviter=house_admin,
        invitee=target,
        house=house,
    )
    client.force_login(house_admin)

    response = client.post(reverse("accounts:cancel_invitation", args=[invitation.id]))

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.status == MembershipInvitation.Status.CANCELLED
    assert AuditLogEntry.objects.filter(action="membership_invitation_cancelled").exists()


@pytest.mark.django_db
def test_staff_cannot_delete_own_account(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    client.force_login(staff)

    response = client.post(reverse("accounts:user_delete", args=[staff.id]))

    assert response.status_code == 302
    assert response.url == reverse("accounts:user_access_detail", args=[staff.id])
    assert get_user_model().objects.filter(id=staff.id).exists()


@pytest.mark.django_db
def test_user_can_change_own_password(client):
    user = create_user("denizen@example.test")
    client.force_login(user)

    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "swordfish",
            "new_password1": "new-swordfish-123",
            "new_password2": "new-swordfish-123",
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("new-swordfish-123")
    assert AuditLogEntry.objects.filter(action="own_password_changed").exists()


@pytest.mark.django_db
def test_admin_can_change_managed_user_password(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("denizen@example.test")
    client.force_login(staff)

    response = client.post(
        reverse("accounts:admin_change_password", args=[target.id]),
        {
            "new_password1": "changed-swordfish-123",
            "new_password2": "changed-swordfish-123",
        },
    )

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.check_password("changed-swordfish-123")
    assert AuditLogEntry.objects.filter(action="user_password_changed").exists()


@pytest.mark.django_db
def test_audit_log_is_superuser_only(client):
    user = create_user("denizen@example.test")
    client.force_login(user)

    response = client.get(reverse("accounts:audit_log"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_audit_detail_is_viewable_by_superuser(client):
    staff = create_user("admin@example.test", staff=True, superuser=True)
    entry = AuditLogEntry.objects.create(
        actor=staff,
        action="test_action",
        target_type="User",
        target_id=str(staff.id),
        target_label=str(staff),
        detail={"field": "value"},
    )
    client.force_login(staff)

    response = client.get(reverse("accounts:audit_log_detail", args=[entry.id]))

    assert response.status_code == 200
    assert b"test_action" in response.content
    assert b"field" in response.content
