import logging

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings

from accounts.models import ApplicationSetting, AuditLogEntry
from accounts.permissions import AuditAction, RolePresetKey
from accounts.services import (
    apply_role_preset,
    changed_fields,
    ensure_default_application_settings,
    log_audit,
    model_snapshot,
    start_upgrade_job,
    upgrade_job_status,
    validate_email_settings,
)
from carta.middleware import SlowQueryLoggingMiddleware


def create_user(email: str, *, staff: bool = False, superuser: bool = False):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name=email.split("@")[0].title(),
        is_staff=staff,
        is_superuser=superuser,
    )


@pytest.mark.django_db
def test_role_preset_registry_applies_expected_group():
    user = create_user("denizen@example.test")

    apply_role_preset(user, RolePresetKey.HOUSE_MANAGER)

    assert user.groups.filter(name="House Manager").exists()


@pytest.mark.django_db
def test_audit_log_adds_actor_and_target_metadata():
    actor = create_user("admin@example.test", staff=True, superuser=True)
    target = create_user("target@example.test")

    entry = log_audit(actor, AuditAction.USER_DISABLED, target, {"reason": "test"})

    assert entry.actor == actor
    assert entry.action == AuditAction.USER_DISABLED
    assert entry.target_type == "User"
    assert entry.target_id == str(target.id)
    assert entry.detail["actor_id"] == str(actor.id)
    assert entry.detail["target_label"] == str(target)
    assert entry.detail["reason"] == "test"


@pytest.mark.django_db
def test_model_snapshot_and_changed_fields_capture_audit_diffs():
    user = create_user("denizen@example.test")
    before = model_snapshot(user, ("display_name", "is_active"))
    user.display_name = "Renamed"
    user.is_active = False
    after = model_snapshot(user, ("display_name", "is_active"))

    assert changed_fields(before, after) == {
        "display_name": {"old": "Denizen", "new": "Renamed"},
        "is_active": {"old": True, "new": False},
    }


def test_validate_email_settings_rejects_bad_smtp_options():
    validation = validate_email_settings(
        {
            "email_backend": "django.core.mail.backends.smtp.EmailBackend",
            "email_host": "",
            "email_port": "70000",
            "email_use_tls": "true",
            "email_use_ssl": "true",
            "email_from_address": "",
        }
    )

    assert not validation.ok
    assert "SMTP backend needs a host." in validation.errors
    assert "Email port must be a number from 1 to 65535." in validation.errors
    assert "Email TLS and SSL cannot both be enabled." in validation.errors
    assert "SMTP backend needs a from address." in validation.errors


def test_validate_email_settings_accepts_console_backend_without_smtp():
    validation = validate_email_settings(
        {
            "email_backend": "django.core.mail.backends.console.EmailBackend",
            "email_host": "",
            "email_port": "",
            "email_use_tls": "false",
            "email_use_ssl": "false",
            "email_from_address": "",
        }
    )

    assert validation.ok


@pytest.mark.django_db
def test_start_upgrade_job_reuses_running_job(monkeypatch):
    started_threads = []

    class FakeThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started_threads.append(self.args[0])

    monkeypatch.setattr("accounts.services.threading.Thread", FakeThread)

    first_job_id = start_upgrade_job()
    second_job_id = start_upgrade_job()

    assert second_job_id == first_job_id
    assert started_threads == [first_job_id]
    assert upgrade_job_status(first_job_id)["status"] == "running"


@pytest.mark.django_db
def test_default_settings_include_slow_query_health_support(settings):
    settings.CARTA_SLOW_QUERY_MS = 200

    ensure_default_application_settings()

    assert ApplicationSetting.objects.filter(key="email_backend").exists()


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0)
def test_slow_query_middleware_can_be_disabled():
    request = RequestFactory().get("/")
    middleware = SlowQueryLoggingMiddleware(lambda request: "ok")

    assert middleware(request) == "ok"


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0)
def test_audit_action_registry_covers_existing_admin_actions():
    actions = {
        AuditAction.APPLICATION_SETTINGS_UPDATED,
        AuditAction.GIT_CHECKOUT_RESET,
        AuditAction.GIT_FILE_RESTORED,
        AuditAction.HOUSE_MEMBERSHIP_REMOVED,
        AuditAction.HOUSE_UPDATED,
        AuditAction.KINGDOM_MEMBERSHIP_REMOVED,
        AuditAction.KINGDOM_UPDATED,
        AuditAction.MEMBERSHIP_INVITATION_ACCEPTED,
        AuditAction.MEMBERSHIP_INVITATION_CANCELLED,
        AuditAction.MEMBERSHIP_INVITATION_CREATED,
        AuditAction.MEMBERSHIP_INVITATION_DECLINED,
        AuditAction.OWN_PASSWORD_CHANGED,
        AuditAction.TEST_EMAIL_SENT,
        AuditAction.UPGRADE_REUSED_RUNNING_JOB,
        AuditAction.UPGRADE_STARTED,
        AuditAction.USER_ACCESS_UPDATED,
        AuditAction.USER_CREATED,
        AuditAction.USER_DISABLED,
        AuditAction.USER_ENABLED,
        AuditAction.USER_PASSWORD_CHANGED,
    }

    assert len(actions) == 20
    assert not AuditLogEntry.objects.filter(action__in=actions).exists()


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0.000001)
def test_slow_query_middleware_logs_queries_over_threshold(caplog):
    request = RequestFactory().get("/status/")
    user = create_user("denizen@example.test")

    def get_response(request):
        get_user_model().objects.get(pk=user.pk)
        return "ok"

    middleware = SlowQueryLoggingMiddleware(get_response)

    with caplog.at_level(logging.WARNING, logger="carta.slow_queries"):
        assert middleware(request) == "ok"

    assert any("Slow query" in record.message for record in caplog.records)
