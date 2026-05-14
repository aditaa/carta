from __future__ import annotations

import io
import platform
import re
import secrets
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

from django import get_version
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q

from accounts.models import ApplicationSetting, AuditLogEntry
from accounts.permissions import ROLE_PRESETS
from installer.services import installer_lock_path
from ownership.models import HouseMembership, KingdomMembership, Role
from rulesets.models import Ruleset

RELEASE_BRANCH_DEFAULT = "stable"
RELEASE_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
RESERVED_RELEASE_BRANCH_NAMES = {
    "HEAD",
    "FETCH_HEAD",
    "ORIG_HEAD",
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
}

DEFAULT_APPLICATION_SETTINGS = [
    {
        "key": "site_name",
        "label": "Site name",
        "value": "Carta Arcanum",
        "description": "Displayed in the header and page titles.",
    },
    {
        "key": "maintenance_notice",
        "label": "Maintenance notice",
        "value": "",
        "description": "Shown above every page when set.",
    },
    {
        "key": "email_backend",
        "label": "Email backend",
        "value": "django.core.mail.backends.console.EmailBackend",
        "description": (
            "Django email backend path. Console backend is safest for local Linux installs."
        ),
    },
    {
        "key": "email_host",
        "label": "SMTP host",
        "value": "localhost",
        "description": "SMTP relay host, provider host, or local mail server.",
    },
    {
        "key": "email_port",
        "label": "SMTP port",
        "value": "25",
        "description": "Common values are 25, 465, 587, or provider-specific ports.",
    },
    {
        "key": "email_use_tls",
        "label": "SMTP TLS",
        "value": "false",
        "description": "Use STARTTLS for SMTP relays and providers that require it.",
    },
    {
        "key": "email_use_ssl",
        "label": "SMTP SSL",
        "value": "false",
        "description": "Use implicit SSL, often with port 465.",
    },
    {
        "key": "email_username",
        "label": "SMTP username",
        "value": "",
        "description": "Username for SMTP relay or provider authentication.",
    },
    {
        "key": "email_password",
        "label": "SMTP password",
        "value": "",
        "description": "Password or token for SMTP relay or provider authentication.",
    },
    {
        "key": "email_from_address",
        "label": "From address",
        "value": "noreply@localhost",
        "description": "Default sender used for account emails.",
    },
    {
        "key": "restart_command",
        "label": "Restart command",
        "value": "",
        "description": "Optional command run after upgrade, such as systemctl restart carta.",
    },
    {
        "key": "release_branch",
        "label": "Release branch",
        "value": RELEASE_BRANCH_DEFAULT,
        "description": (
            "Git branch used by in-app upgrades. "
            "Use stable for releases or main for dev/test installs."
        ),
    },
    {
        "key": "restart_required",
        "label": "Restart required",
        "value": "false",
        "description": "Set by upgrades when the app process still needs a restart.",
    },
    {
        "key": "telemetry_enabled",
        "label": "Anonymous performance telemetry",
        "value": "true",
        "description": (
            "Allow Carta Arcanum to send anonymous route timing, status, and query-count "
            "metrics when a telemetry endpoint is configured."
        ),
    },
    {
        "key": "telemetry_endpoint",
        "label": "Telemetry endpoint",
        "value": "",
        "description": (
            "Optional HTTPS URL that receives anonymous performance telemetry. "
            "Leave blank to avoid sending data off this install."
        ),
    },
    {
        "key": "sentry_enabled",
        "label": "Sentry telemetry",
        "value": "true",
        "description": (
            "Allow anonymous error and performance reports to be sent to Sentry when a "
            "Sentry DSN is configured."
        ),
    },
    {
        "key": "sentry_dsn",
        "label": "Sentry DSN",
        "value": (
            "https://538e7483cd26762751c6535ff2428f5c"
            "@o4511390011949056.ingest.us.sentry.io/4511390014177280"
        ),
        "description": (
            "Optional Sentry project DSN. Use the maintainer-provided DSN to share "
            "anonymous install telemetry, or use your own Sentry project."
        ),
    },
    {
        "key": "sentry_traces_sample_rate",
        "label": "Sentry traces sample rate",
        "value": "0.05",
        "description": (
            "Fraction of request performance traces sent to Sentry, from 0.0 to 1.0. "
            "The default samples about five percent of requests."
        ),
    },
    {
        "key": "sentry_profiles_sample_rate",
        "label": "Sentry profiles sample rate",
        "value": "0.01",
        "description": (
            "Fraction of sampled Sentry transactions that include code profiling data, "
            "from 0.0 to 1.0. The default profiles about one percent."
        ),
    },
    {
        "key": "sentry_environment",
        "label": "Sentry environment",
        "value": "community-install",
        "description": "Environment label used for Sentry events from this installation.",
    },
    {
        "key": "bug_report_repository",
        "label": "Bug report GitHub repository",
        "value": "aditaa/carta",
        "description": "GitHub owner/repository used for prefilled in-app bug reports.",
    },
]

UPGRADE_JOBS: dict[str, dict[str, str]] = {}
UPGRADE_JOBS_LOCK = threading.Lock()


@dataclass(frozen=True)
class HealthCheck:
    label: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class EmailSettingsValidation:
    ok: bool
    errors: tuple[str, ...] = ()


def ensure_default_application_settings() -> list[ApplicationSetting]:
    settings_rows = []
    for setting in DEFAULT_APPLICATION_SETTINGS:
        row, _ = ApplicationSetting.objects.get_or_create(
            key=setting["key"],
            defaults={
                "label": setting["label"],
                "value": setting["value"],
                "description": setting["description"],
            },
        )
        settings_rows.append(row)
    return settings_rows


def application_setting_map() -> dict[str, str]:
    ensure_default_application_settings()
    return dict(ApplicationSetting.objects.values_list("key", "value"))


def status_health_checks() -> list[HealthCheck]:
    checks = [
        HealthCheck(
            "Linux runtime",
            platform.system() == "Linux",
            f"Detected {platform.system()}. Carta Arcanum is supported on Linux/WSL.",
        ),
        HealthCheck("Python", sys.version_info >= (3, 11), platform.python_version()),
        HealthCheck("Django", True, get_version()),
        _database_check(),
        HealthCheck(
            "Rules file",
            settings.CURRENT_RULES_FILE.exists(),
            str(settings.CURRENT_RULES_FILE),
        ),
        HealthCheck(
            "Imported rulesets",
            Ruleset.objects.exists(),
            f"{Ruleset.objects.count()} rulesets imported.",
        ),
        HealthCheck(
            "Installer lock",
            installer_lock_path().exists(),
            str(installer_lock_path()),
        ),
        _migration_check(),
        _path_writable_check("Static root", settings.STATIC_ROOT),
        _path_writable_check("Media root", settings.MEDIA_ROOT),
        _email_settings_check(),
        _release_branch_check(),
        _restart_required_check(),
        _slow_query_monitor_check(),
    ]
    checks.append(git_status_check())
    checks.append(git_file_integrity_check())
    return checks


def git_status_check() -> HealthCheck:
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_git(["rev-parse", "--short", "HEAD"])
    upstream = _run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if branch.returncode != 0 or commit.returncode != 0:
        return HealthCheck("Git checkout", False, "This install is not in a readable Git checkout.")
    if upstream.returncode != 0:
        detail = f"{branch.stdout.strip()} @ {commit.stdout.strip()}"
        return HealthCheck("Git checkout", True, detail)

    divergence = _run_git(
        ["rev-list", "--left-right", "--count", f"HEAD...{upstream.stdout.strip()}"]
    )
    if divergence.returncode != 0:
        detail = (
            f"{branch.stdout.strip()} @ {commit.stdout.strip()}, upstream {upstream.stdout.strip()}"
        )
        return HealthCheck("Git checkout", True, detail)

    ahead, behind = divergence.stdout.strip().split()
    detail = (
        f"{branch.stdout.strip()} @ {commit.stdout.strip()}, "
        f"{ahead} ahead / {behind} behind {upstream.stdout.strip()}"
    )
    return HealthCheck("Git checkout", behind == "0", detail)


def upgrade_available() -> bool:
    release_branch = configured_release_branch()
    target_ref = f"origin/{release_branch}"
    if not _git_ref_exists(target_ref):
        return False
    divergence = _run_git(["rev-list", "--left-right", "--count", f"HEAD...{target_ref}"])
    if divergence.returncode != 0:
        return False
    try:
        _ahead, behind = divergence.stdout.strip().split()
    except ValueError:
        return False
    return behind != "0"


def git_file_integrity_check() -> HealthCheck:
    changed = git_changed_files()
    if not changed:
        return HealthCheck("Git file integrity", True, "No tracked files differ from Git.")
    detail = ", ".join(changed[:8])
    if len(changed) > 8:
        detail = f"{detail}, and {len(changed) - 8} more"
    return HealthCheck("Git file integrity", False, detail)


def git_changed_files() -> list[str]:
    status = _run_git(["status", "--porcelain", "--untracked-files=no"])
    if status.returncode != 0:
        return []
    files = []
    for line in status.stdout.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def restore_git_file(path: str) -> None:
    if path not in git_changed_files():
        raise ValueError("That file is not listed as changed by Git.")
    _run_git_checked(["restore", "--source=HEAD", "--staged", "--worktree", "--", path])


def reset_git_checkout() -> None:
    _run_git_checked(["reset", "--hard", "HEAD"])


def start_upgrade_job() -> str:
    with UPGRADE_JOBS_LOCK:
        for existing_job_id, job in UPGRADE_JOBS.items():
            if job.get("status") == "running":
                return existing_job_id
        job_id = secrets.token_urlsafe(16)
        UPGRADE_JOBS[job_id] = {
            "status": "running",
            "message": "Starting upgrade",
            "output": "",
            "error": "",
        }
    thread = threading.Thread(target=_run_upgrade_job, args=(job_id,), daemon=True)
    thread.start()
    return job_id


def upgrade_job_status(job_id: str) -> dict[str, str]:
    with UPGRADE_JOBS_LOCK:
        return UPGRADE_JOBS.get(job_id, {}).copy()


def _run_upgrade_job(job_id: str) -> None:
    output = _UpgradeOutputLog(job_id)
    close_old_connections()
    try:
        release_branch = configured_release_branch()
        _update_upgrade_job(job_id, message="Resetting tracked files to Git")
        _append_completed_command(output, ["git", "reset", "--hard", "HEAD"])

        _update_upgrade_job(job_id, message="Fetching latest code")
        _append_completed_command(output, ["git", "fetch", "--all", "--prune"])

        _update_upgrade_job(job_id, message=f"Switching to {release_branch} branch")
        _append_completed_command(output, ["git", "checkout", release_branch])

        _update_upgrade_job(job_id, message="Pulling fast-forward updates")
        _append_completed_command(output, ["git", "pull", "--ff-only", "origin", release_branch])

        _update_upgrade_job(job_id, message="Running database migrations")
        output.write("\n$ python manage.py migrate --noinput\n")
        call_command("migrate", stdout=output, no_input=True)

        _update_upgrade_job(job_id, message="Collecting static files")
        output.write("\n$ python manage.py collectstatic --noinput\n")
        call_command("collectstatic", stdout=output, no_input=True, verbosity=1)

        restart_command = application_setting_map().get("restart_command", "").strip()
        if restart_command:
            _update_upgrade_job(job_id, message="Restarting application")
            _append_completed_command(output, shlex.split(restart_command))
            _set_application_setting("restart_required", "false")
        else:
            _set_application_setting("restart_required", "true")
    except Exception as exc:
        _update_upgrade_job(
            job_id,
            status="error",
            message="Upgrade failed",
            output=output.getvalue(),
            error=str(exc),
        )
    else:
        _update_upgrade_job(
            job_id,
            status="complete",
            message="Upgrade completed",
            output=output.getvalue(),
        )
    finally:
        close_old_connections()


class _UpgradeOutputLog(io.StringIO):
    def __init__(self, job_id: str) -> None:
        super().__init__()
        self.job_id = job_id

    def write(self, value: str) -> int:
        written = super().write(value)
        _update_upgrade_job(self.job_id, output=self.getvalue())
        return written


def _append_completed_command(output: io.StringIO, command: list[str]) -> None:
    output.write(f"$ {' '.join(command)}\n")
    completed = subprocess.run(
        command,
        cwd=settings.BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    output.write(completed.stdout)
    output.write(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed with exit code {completed.returncode}.")


def _database_check() -> HealthCheck:
    start = time.perf_counter()
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return HealthCheck("Database", False, str(exc))
    elapsed_ms = (time.perf_counter() - start) * 1000
    detail = f"{connection.settings_dict['ENGINE']} · {elapsed_ms:.1f} ms"
    return HealthCheck("Database", True, detail)


def _migration_check() -> HealthCheck:
    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
    except Exception as exc:
        return HealthCheck("Migrations", False, str(exc))
    if plan:
        return HealthCheck("Migrations", False, f"{len(plan)} unapplied migrations.")
    return HealthCheck("Migrations", True, "All migrations applied.")


def _path_writable_check(label: str, path) -> HealthCheck:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".carta-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return HealthCheck(label, False, str(exc))
    return HealthCheck(label, True, str(path))


def _email_settings_check() -> HealthCheck:
    settings_map = application_setting_map()
    backend = settings_map.get("email_backend", "")
    host = settings_map.get("email_host", "")
    port = settings_map.get("email_port", "")
    validation = validate_email_settings(settings_map)
    if not validation.ok:
        return HealthCheck("Email settings", False, "; ".join(validation.errors))
    return HealthCheck("Email settings", True, f"{backend} via {host}:{port}")


def validate_email_settings(settings_map: dict[str, str]) -> EmailSettingsValidation:
    backend = settings_map.get("email_backend", "").strip()
    host = settings_map.get("email_host", "").strip()
    port = settings_map.get("email_port", "").strip()
    from_address = settings_map.get("email_from_address", "").strip()
    use_tls = settings_map.get("email_use_tls", "").strip().lower() == "true"
    use_ssl = settings_map.get("email_use_ssl", "").strip().lower() == "true"
    errors = []
    if not backend:
        errors.append("Email backend is not configured.")
    if port and (not port.isdigit() or not 1 <= int(port) <= 65535):
        errors.append("Email port must be a number from 1 to 65535.")
    if use_tls and use_ssl:
        errors.append("Email TLS and SSL cannot both be enabled.")
    if "smtp" in backend.lower():
        if not host:
            errors.append("SMTP backend needs a host.")
        if not port:
            errors.append("SMTP backend needs a port.")
        if not from_address:
            errors.append("SMTP backend needs a from address.")
    return EmailSettingsValidation(ok=not errors, errors=tuple(errors))


def configured_release_branch(settings_map: dict[str, str] | None = None) -> str:
    settings_map = settings_map or application_setting_map()
    branch = settings_map.get("release_branch", RELEASE_BRANCH_DEFAULT).strip()
    return branch or RELEASE_BRANCH_DEFAULT


def validate_release_branch(branch: str) -> tuple[bool, str]:
    branch = branch.strip()
    if not branch:
        return False, "Release branch is required."
    if branch.upper() in RESERVED_RELEASE_BRANCH_NAMES:
        return False, "Release branch must be a named branch, not a symbolic Git ref."
    if branch.startswith("-"):
        return False, "Release branch cannot start with a dash."
    if (
        branch.endswith("/")
        or branch.endswith(".")
        or branch.endswith(".lock")
        or branch.startswith("/")
        or "//" in branch
        or ".." in branch
        or "@{" in branch
    ):
        return False, "Release branch must be a normal Git branch name."
    if not RELEASE_BRANCH_PATTERN.fullmatch(branch):
        return (
            False,
            "Release branch can only contain letters, numbers, dots, dashes, "
            "underscores, and slashes.",
        )
    return True, ""


def _release_branch_check() -> HealthCheck:
    release_branch = configured_release_branch()
    valid, error = validate_release_branch(release_branch)
    if not valid:
        return HealthCheck("Release branch", False, error)
    target_ref = f"origin/{release_branch}"
    if not _git_ref_exists(target_ref):
        return HealthCheck("Release branch", False, f"{target_ref} is not available locally.")
    return HealthCheck("Release branch", True, release_branch)


def _restart_required_check() -> HealthCheck:
    required = application_setting_map().get("restart_required", "false").lower() == "true"
    if required:
        return HealthCheck("Restart needed", False, "Application restart is required.")
    return HealthCheck("Restart needed", True, "No pending restart flag.")


def _slow_query_monitor_check() -> HealthCheck:
    threshold_ms = getattr(settings, "CARTA_SLOW_QUERY_MS", 0)
    if threshold_ms <= 0:
        return HealthCheck(
            "Slow query monitor",
            True,
            "Disabled. Set CARTA_SLOW_QUERY_MS to enable.",
        )
    return HealthCheck("Slow query monitor", True, f"Logging queries over {threshold_ms} ms.")


def _set_application_setting(key: str, value: str) -> None:
    ensure_default_application_settings()
    ApplicationSetting.objects.filter(key=key).update(value=value)


def _run_git(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *command],
        cwd=settings.BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def _run_git_checked(command: list[str]) -> None:
    completed = _run_git(command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "Git command failed.")


def _git_ref_exists(ref: str) -> bool:
    return _run_git(["rev-parse", "--verify", "--quiet", ref]).returncode == 0


def _update_upgrade_job(job_id: str, **changes: str) -> None:
    with UPGRADE_JOBS_LOCK:
        if job_id in UPGRADE_JOBS:
            UPGRADE_JOBS[job_id].update(changes)


def log_audit(actor, action: str, target, detail: dict | None = None) -> AuditLogEntry:
    actor_id = str(getattr(actor, "pk", "")) if getattr(actor, "is_authenticated", False) else ""
    actor_label = str(actor) if getattr(actor, "is_authenticated", False) else "System"
    target_type = target.__class__.__name__
    target_id = str(getattr(target, "pk", ""))
    target_label = str(target)
    audit_detail = {
        "actor_id": actor_id,
        "actor_label": actor_label,
        "target_type": target_type,
        "target_id": target_id,
        "target_label": target_label,
    }
    audit_detail.update(detail or {})
    return AuditLogEntry.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        detail=audit_detail,
    )


def model_snapshot(instance, fields: tuple[str, ...]) -> dict[str, str | bool | None]:
    return {field: getattr(instance, field) for field in fields}


def changed_fields(before: dict, after: dict) -> dict[str, dict[str, object]]:
    return {
        key: {"old": before.get(key), "new": after.get(key)}
        for key in before.keys() | after.keys()
        if before.get(key) != after.get(key)
    }


def ensure_default_role_groups() -> list[Group]:
    groups = []
    for preset in ROLE_PRESETS.values():
        group, _ = Group.objects.get_or_create(name=preset.name)
        permissions = []
        for permission_name in preset.permissions:
            app_label, codename = permission_name.split(".", 1)
            try:
                permissions.append(
                    Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                )
            except Permission.DoesNotExist:
                continue
        group.permissions.set(permissions)
        groups.append(group)
    return groups


def role_preset_choices() -> list[tuple[str, str]]:
    ensure_default_role_groups()
    return [("", "Custom permissions")] + [
        (key, preset.name) for key, preset in ROLE_PRESETS.items()
    ]


def apply_role_preset(user, preset_key: str) -> None:
    if not preset_key:
        return
    if preset_key not in ROLE_PRESETS:
        raise ValidationError("Unknown role preset.")
    ensure_default_role_groups()
    group_name = ROLE_PRESETS[preset_key].name
    user.groups.add(Group.objects.get(name=group_name))


def can_manage_user(viewer, target_user) -> bool:
    if not getattr(viewer, "is_active", False):
        return False
    if viewer.is_superuser:
        return True
    if viewer.pk == target_user.pk:
        return True
    if target_user.is_superuser or target_user.is_staff:
        return False

    viewer_kingdom_ids = KingdomMembership.objects.filter(
        user=viewer,
        active=True,
        role=Role.ADMIN,
    ).values("kingdom_id")
    target_kingdom_ids = KingdomMembership.objects.filter(
        user=target_user,
        active=True,
    ).values("kingdom_id")
    if (
        KingdomMembership.objects.filter(
            user=target_user,
            active=True,
            kingdom_id__in=viewer_kingdom_ids,
        ).exists()
        or KingdomMembership.objects.filter(
            user=viewer,
            active=True,
            role=Role.ADMIN,
            kingdom_id__in=target_kingdom_ids,
        ).exists()
    ):
        return True

    viewer_house_ids = HouseMembership.objects.filter(
        user=viewer,
        active=True,
        role=Role.ADMIN,
    ).values("house_id")
    return HouseMembership.objects.filter(
        user=target_user,
        active=True,
        house_id__in=viewer_house_ids,
    ).exists()


def manageable_user_queryset(viewer):
    user_model = get_user_model()
    if not getattr(viewer, "is_active", False):
        return user_model.objects.none()
    if viewer.is_superuser:
        return user_model.objects.all()

    house_ids = HouseMembership.objects.filter(
        user=viewer,
        active=True,
        role=Role.ADMIN,
    ).values("house_id")
    kingdom_ids = KingdomMembership.objects.filter(
        user=viewer,
        active=True,
        role=Role.ADMIN,
    ).values("kingdom_id")
    user_ids = set(
        HouseMembership.objects.filter(house_id__in=house_ids).values_list("user_id", flat=True)
    )
    user_ids.update(
        KingdomMembership.objects.filter(kingdom_id__in=kingdom_ids).values_list(
            "user_id",
            flat=True,
        )
    )
    user_ids.add(viewer.pk)
    return user_model.objects.filter(Q(id__in=user_ids) & (Q(id=viewer.pk) | Q(is_staff=False)))
