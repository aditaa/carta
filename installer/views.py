import io

from django.conf import settings
from django.core.management import call_command
from django.shortcuts import render

from installer.forms import DatabaseConfigForm
from installer.services import (
    DatabaseConfig,
    current_database_config,
    installer_is_locked,
    test_mysql_connection,
    write_database_env,
)


def index(request):
    return render(request, "installer/index.html", {"locked": installer_is_locked()})


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


def application_setup(request):
    if installer_is_locked():
        return render(request, "installer/locked.html")

    command_output = ""
    command_error = ""
    completed = False
    if request.method == "POST":
        stdout = io.StringIO()
        try:
            call_command("migrate", stdout=stdout, no_input=True)
            call_command(
                "import_rules",
                settings.BASE_DIR / "rules" / "carta-arcanum-2.1.4.rules.json",
                stdout=stdout,
            )
        except Exception as exc:
            command_error = str(exc)
        else:
            completed = True
        command_output = stdout.getvalue()

    return render(
        request,
        "installer/application.html",
        {
            "completed": completed,
            "command_error": command_error,
            "command_output": command_output,
        },
    )


def _config_from_form(form: DatabaseConfigForm) -> DatabaseConfig:
    return DatabaseConfig(
        host=form.cleaned_data["host"],
        port=form.cleaned_data["port"],
        database=form.cleaned_data["database"],
        test_database=form.cleaned_data["test_database"],
        user=form.cleaned_data["user"],
        password=form.cleaned_data["password"],
    )
