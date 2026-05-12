import io
import secrets
import threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.signing import BadSignature
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from installer.forms import DatabaseConfigForm, InstallerSuperUserForm
from installer.services import (
    DatabaseConfig,
    apply_database_config,
    current_database_config,
    installer_is_locked,
    lock_installer,
    prerequisite_checks,
    test_mysql_connection,
    write_database_env,
)

INSTALLER_SUPERUSER_COOKIE = "carta_installer_superuser"
INSTALLER_SUPERUSER_PAYLOADS: dict[str, dict[str, str]] = {}
INSTALLER_SETUP_JOBS: dict[str, dict[str, str | bool]] = {}
INSTALLER_SETUP_JOBS_LOCK = threading.Lock()


def index(request):
    if installer_is_locked():
        return render(request, "installer/locked.html")
    checks = prerequisite_checks()
    return render(
        request,
        "installer/index.html",
        {
            "checks": checks,
            "can_continue": all(check["ok"] for check in checks),
        },
    )


def database_setup(request):
    if installer_is_locked():
        return render(request, "installer/locked.html")

    saved = False
    connection_error = ""
    if request.method == "POST":
        form = DatabaseConfigForm(request.POST)
        if form.is_valid():
            config = _config_from_form(form)
            try:
                test_mysql_connection(config)
            except Exception as exc:
                connection_error = str(exc)
            else:
                write_database_env(config)
                apply_database_config(config)
                saved = True
    else:
        form = DatabaseConfigForm(initial=current_database_config().__dict__)

    return render(
        request,
        "installer/database.html",
        {
            "form": form,
            "saved": saved,
            "connection_error": connection_error,
        },
    )


def superuser_setup(request):
    if installer_is_locked():
        return render(request, "installer/locked.html")

    if request.method == "POST":
        form = InstallerSuperUserForm(request.POST)
        if form.is_valid():
            token = secrets.token_urlsafe(32)
            INSTALLER_SUPERUSER_PAYLOADS[token] = form.session_payload()
            response = redirect("installer:application")
            response.set_signed_cookie(
                INSTALLER_SUPERUSER_COOKIE,
                token,
                salt=INSTALLER_SUPERUSER_COOKIE,
                max_age=3600,
                httponly=True,
                samesite="Strict",
            )
            return response
    else:
        form = InstallerSuperUserForm()

    return render(request, "installer/superuser.html", {"form": form})


def application_setup(request):
    if installer_is_locked():
        return render(request, "installer/locked.html")

    command_output = ""
    command_error = ""
    completed = False
    job_id = ""
    superuser = _installer_superuser_from_cookie(request)
    if request.method == "POST":
        if not superuser:
            command_error = "Create the installer admin account before running setup."
        else:
            job_id = start_application_setup_job(superuser)
            _clear_installer_superuser(request)
    response = render(
        request,
        "installer/application.html",
        {
            "completed": completed,
            "command_error": command_error,
            "command_output": command_output,
            "has_superuser": bool(superuser),
            "job_id": job_id,
            "job_started": bool(job_id),
        },
    )
    if job_id:
        response.delete_cookie(INSTALLER_SUPERUSER_COOKIE)
    return response


def application_setup_status(request, job_id: str):
    with INSTALLER_SETUP_JOBS_LOCK:
        job = INSTALLER_SETUP_JOBS.get(job_id, {}).copy()
    if not job:
        return JsonResponse({"status": "missing", "error": "Setup job was not found."}, status=404)
    if job.get("status") == "complete":
        job["redirect_url"] = reverse("accounts:login")
    return JsonResponse(job)


def start_application_setup_job(superuser: dict[str, str]) -> str:
    job_id = secrets.token_urlsafe(16)
    with INSTALLER_SETUP_JOBS_LOCK:
        INSTALLER_SETUP_JOBS[job_id] = {
            "status": "running",
            "message": "Starting setup",
            "output": "",
            "error": "",
        }
    thread = threading.Thread(
        target=_run_application_setup_job,
        args=(job_id, superuser),
        daemon=True,
    )
    thread.start()
    return job_id


def _run_application_setup_job(job_id: str, superuser: dict[str, str]) -> None:
    stdout = io.StringIO()
    close_old_connections()
    try:
        _update_application_setup_job(job_id, message="Running database migrations")
        call_command("migrate", stdout=stdout, no_input=True)
        _update_application_setup_job(job_id, output=stdout.getvalue())

        _update_application_setup_job(job_id, message="Importing the current rules file")
        call_command(
            "import_rules",
            settings.CURRENT_RULES_FILE,
            stdout=stdout,
        )
        _update_application_setup_job(job_id, output=stdout.getvalue())

        _update_application_setup_job(job_id, message="Creating the superuser")
        _create_installer_superuser(superuser)

        _update_application_setup_job(job_id, message="Locking the installer")
        lock_installer()
    except Exception as exc:
        _update_application_setup_job(
            job_id,
            status="error",
            message="Setup failed",
            output=stdout.getvalue(),
            error=str(exc),
        )
    else:
        _update_application_setup_job(
            job_id,
            status="complete",
            message="Setup completed. The installer is now locked.",
            output=stdout.getvalue(),
        )
    finally:
        close_old_connections()


def _update_application_setup_job(job_id: str, **changes: str) -> None:
    with INSTALLER_SETUP_JOBS_LOCK:
        if job_id in INSTALLER_SETUP_JOBS:
            INSTALLER_SETUP_JOBS[job_id].update(changes)


def _installer_superuser_from_cookie(request) -> dict[str, str] | None:
    try:
        payload = request.get_signed_cookie(
            INSTALLER_SUPERUSER_COOKIE,
            salt=INSTALLER_SUPERUSER_COOKIE,
        )
    except (BadSignature, KeyError):
        return None
    return INSTALLER_SUPERUSER_PAYLOADS.get(payload)


def _clear_installer_superuser(request) -> None:
    try:
        token = request.get_signed_cookie(
            INSTALLER_SUPERUSER_COOKIE,
            salt=INSTALLER_SUPERUSER_COOKIE,
        )
    except (BadSignature, KeyError):
        return
    INSTALLER_SUPERUSER_PAYLOADS.pop(token, None)


def _config_from_form(form: DatabaseConfigForm) -> DatabaseConfig:
    return DatabaseConfig(
        host=form.cleaned_data["host"],
        port=form.cleaned_data["port"],
        database=form.cleaned_data["database"],
        test_database=form.cleaned_data["test_database"],
        user=form.cleaned_data["user"],
        password=form.cleaned_data["password"],
    )


def _create_installer_superuser(payload: dict[str, str]):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=payload["email"],
        defaults={
            "display_name": payload["display_name"],
            "is_staff": True,
            "is_superuser": True,
        },
    )
    user.display_name = payload["display_name"]
    user.is_staff = True
    user.is_superuser = True
    user.set_password(payload["password"])
    user.save()
    return user
