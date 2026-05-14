import logging
import subprocess
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

import accounts.services as account_services
import carta.telemetry as telemetry
from accounts.bug_reports import CRASH_REPORT_SESSION_KEY
from accounts.models import ApplicationSetting, AuditLogEntry
from accounts.permissions import AuditAction, RolePresetKey
from accounts.services import (
    apply_role_preset,
    changed_fields,
    configured_release_branch,
    ensure_default_application_settings,
    log_audit,
    model_snapshot,
    start_upgrade_job,
    upgrade_available,
    upgrade_job_status,
    validate_email_settings,
    validate_release_branch,
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
def test_default_settings_include_anonymous_telemetry_toggle():
    ensure_default_application_settings()

    assert ApplicationSetting.objects.get(key="telemetry_enabled").value == "true"
    assert ApplicationSetting.objects.get(key="telemetry_endpoint").value == ""
    assert ApplicationSetting.objects.get(key="sentry_enabled").value == "true"
    assert (
        ApplicationSetting.objects.get(key="sentry_dsn").value
        == "https://538e7483cd26762751c6535ff2428f5c"
        "@o4511390011949056.ingest.us.sentry.io/4511390014177280"
    )
    assert ApplicationSetting.objects.get(key="sentry_traces_sample_rate").value == "0.05"
    assert ApplicationSetting.objects.get(key="bug_report_repository").value == "aditaa/carta"


@pytest.mark.django_db
def test_default_settings_include_stable_release_branch():
    ensure_default_application_settings()

    assert ApplicationSetting.objects.get(key="release_branch").value == "stable"
    assert configured_release_branch() == "stable"


@pytest.mark.django_db
def test_configured_release_branch_can_use_main_for_dev_installs():
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="release_branch").update(value="main")

    assert configured_release_branch() == "main"


def test_validate_release_branch_rejects_unsafe_names():
    assert validate_release_branch("main") == (True, "")
    assert validate_release_branch("stable") == (True, "")
    assert validate_release_branch("release/2026-05") == (True, "")

    assert not validate_release_branch("")[0]
    assert not validate_release_branch("-main")[0]
    assert not validate_release_branch("feature//bad")[0]
    assert not validate_release_branch("feature bad")[0]
    assert not validate_release_branch("HEAD")[0]
    assert not validate_release_branch("refs/heads/main.lock")[0]
    assert not validate_release_branch("release/@{bad}")[0]


@pytest.mark.django_db
def test_upgrade_available_uses_configured_release_branch(monkeypatch):
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="release_branch").update(value="main")
    checked_refs = []
    commands = []

    def fake_git_ref_exists(ref):
        checked_refs.append(ref)
        return True

    def fake_run_git(command):
        commands.append(command)
        return subprocess.CompletedProcess(
            ["git", *command],
            0,
            stdout="0\t1\n",
            stderr="",
        )

    monkeypatch.setattr("accounts.services._git_ref_exists", fake_git_ref_exists)
    monkeypatch.setattr("accounts.services._run_git", fake_run_git)

    assert upgrade_available()
    assert checked_refs == ["origin/main"]
    assert commands == [["rev-list", "--left-right", "--count", "HEAD...origin/main"]]


def test_reset_git_checkout_preserves_untracked_runtime_files(monkeypatch):
    commands = []

    def fake_run_git_checked(command):
        commands.append(command)

    monkeypatch.setattr("accounts.services._run_git_checked", fake_run_git_checked)

    account_services.reset_git_checkout()

    assert commands == [["reset", "--hard", "HEAD"]]
    assert ["clean", "-fd"] not in commands


@pytest.mark.django_db
def test_upgrade_job_checks_out_configured_release_branch(monkeypatch):
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="release_branch").update(value="main")
    account_services.UPGRADE_JOBS["job-123"] = {
        "status": "running",
        "message": "Starting upgrade",
        "output": "",
        "error": "",
    }
    commands = []

    def fake_completed_command(output, command):
        commands.append(command)
        output.write(f"$ {' '.join(command)}\n")

    monkeypatch.setattr("accounts.services._append_completed_command", fake_completed_command)
    monkeypatch.setattr("accounts.services.call_command", lambda *args, **kwargs: None)
    monkeypatch.setattr("accounts.services.close_old_connections", lambda: None)

    account_services._run_upgrade_job("job-123")

    assert ["git", "reset", "--hard", "HEAD"] in commands
    assert ["git", "clean", "-fd"] not in commands
    assert ["git", "checkout", "main"] in commands
    assert ["git", "pull", "--ff-only", "origin", "main"] in commands
    assert upgrade_job_status("job-123")["status"] == "complete"
    account_services.UPGRADE_JOBS.pop("job-123", None)


@pytest.mark.django_db
def test_upgrade_job_publishes_management_command_output(monkeypatch):
    ensure_default_application_settings()
    account_services.UPGRADE_JOBS["job-output"] = {
        "status": "running",
        "message": "Starting upgrade",
        "output": "",
        "error": "",
    }

    def fake_completed_command(output, command):
        output.write(f"$ {' '.join(command)}\n")

    def fake_call_command(command_name, *, stdout, **kwargs):
        stdout.write(f"{command_name} started\n")
        assert f"{command_name} started" in upgrade_job_status("job-output")["output"]

    monkeypatch.setattr("accounts.services._append_completed_command", fake_completed_command)
    monkeypatch.setattr("accounts.services.call_command", fake_call_command)
    monkeypatch.setattr("accounts.services.close_old_connections", lambda: None)

    account_services._run_upgrade_job("job-output")

    job = upgrade_job_status("job-output")
    assert "$ python manage.py migrate --noinput" in job["output"]
    assert "migrate started" in job["output"]
    assert "$ python manage.py collectstatic --noinput" in job["output"]
    assert "collectstatic started" in job["output"]
    account_services.UPGRADE_JOBS.pop("job-output", None)


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


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0)
def test_middleware_sends_anonymous_performance_telemetry(monkeypatch):
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="telemetry_endpoint").update(
        value="https://telemetry.example.test/carta"
    )
    sent_payloads = []

    class FakeThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            sent_payloads.append(self.args)

    request = RequestFactory().get("/accounts/users/123/?email=secret@example.test")
    request.resolver_match = SimpleNamespace(view_name="accounts:user_access_detail")
    middleware = SlowQueryLoggingMiddleware(lambda request: HttpResponse("ok", status=202))

    monkeypatch.setattr("carta.telemetry.threading.Thread", FakeThread)

    response = middleware(request)

    assert response.status_code == 202
    assert len(sent_payloads) == 1
    endpoint, payload = sent_payloads[0]
    assert endpoint == "https://telemetry.example.test/carta"
    assert payload["schema"] == "carta.performance.v1"
    assert payload["request"]["route"] == "accounts:user_access_detail"
    assert payload["request"]["method"] == "GET"
    assert payload["request"]["status_code"] == 202
    assert "path" not in payload["request"]
    assert "user" not in payload


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0)
def test_middleware_skips_telemetry_without_endpoint(monkeypatch):
    ensure_default_application_settings()
    started_threads = []

    class FakeThread:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def start(self):
            started_threads.append(self.kwargs)

    request = RequestFactory().get("/")
    middleware = SlowQueryLoggingMiddleware(lambda request: HttpResponse("ok"))

    monkeypatch.setattr("carta.telemetry.threading.Thread", FakeThread)

    middleware(request)

    assert started_threads == []


@pytest.mark.django_db
@override_settings(CARTA_SLOW_QUERY_MS=0)
def test_middleware_records_crash_for_bug_report(monkeypatch):
    request = RequestFactory().get("/accounts/users/123/?email=secret@example.test")
    request.resolver_match = SimpleNamespace(view_name="accounts:user_access_detail")
    request.session = {}
    middleware = SlowQueryLoggingMiddleware(
        lambda request: (_ for _ in ()).throw(ValueError("secret email"))
    )
    monkeypatch.setattr("carta.middleware.capture_sentry_exception", lambda *args, **kwargs: None)

    with pytest.raises(ValueError):
        middleware(request)

    crash_report = request.session[CRASH_REPORT_SESSION_KEY]
    assert crash_report["exception_type"] == "ValueError"
    assert crash_report["route"] == "accounts:user_access_detail"
    assert crash_report["method"] == "GET"
    assert "path" not in crash_report
    assert "secret" not in str(crash_report).lower()


@pytest.mark.django_db
def test_sentry_configures_without_default_pii(monkeypatch):
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="sentry_dsn").update(
        value="https://public@example.ingest.sentry.io/1"
    )
    init_calls = []

    class FakeSentry:
        def init(self, **kwargs):
            init_calls.append(kwargs)

    monkeypatch.setattr("carta.telemetry.sentry_sdk", FakeSentry())
    monkeypatch.setattr("carta.telemetry._SENTRY_CONFIGURED_KEY", None)

    config = telemetry.configure_sentry()

    assert config.dsn == "https://public@example.ingest.sentry.io/1"
    assert config.traces_sample_rate == 0.05
    assert init_calls[0]["send_default_pii"] is False
    assert init_calls[0]["before_send"] is telemetry._scrub_sentry_event
    assert init_calls[0]["before_send_transaction"] is telemetry._scrub_sentry_event


@pytest.mark.django_db
def test_sentry_does_not_configure_without_dsn(monkeypatch):
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key="sentry_dsn").update(value="")
    init_calls = []

    class FakeSentry:
        def init(self, **kwargs):
            init_calls.append(kwargs)

    monkeypatch.setattr("carta.telemetry.sentry_sdk", FakeSentry())
    monkeypatch.setattr("carta.telemetry._SENTRY_CONFIGURED_KEY", None)

    assert telemetry.configure_sentry() is None
    assert init_calls == []


def test_sentry_scrubber_removes_pii_shaped_event_data():
    event = {
        "user": {"email": "denizen@example.test"},
        "request": {
            "url": "https://example.test/accounts/users/123/?email=denizen@example.test",
            "query_string": "email=denizen@example.test",
            "data": {"password": "secret"},
            "headers": {"cookie": "sessionid=secret"},
            "method": "POST",
        },
        "breadcrumbs": {"values": [{"message": "secret"}]},
        "extra": {"sql": "SELECT * FROM accounts_user"},
    }

    scrubbed = telemetry._scrub_sentry_event(event, {})

    assert "user" not in scrubbed
    assert scrubbed["request"] == {"method": "POST"}
    assert "breadcrumbs" not in scrubbed
    assert "extra" not in scrubbed
