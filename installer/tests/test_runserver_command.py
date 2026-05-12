import io

from django.core.management.base import OutputWrapper

from installer.management.commands import runserver


def test_runserver_allows_first_install_when_migration_check_cannot_connect(monkeypatch):
    def fail_migration_check(command):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        runserver.BaseRunserverCommand,
        "check_migrations",
        fail_migration_check,
    )
    command = runserver.Command()
    stderr = io.StringIO()
    command.stderr = OutputWrapper(stderr)

    command.check_migrations()

    assert "continue to the web installer" in stderr.getvalue()


def test_runserver_uses_normal_migration_check_when_database_is_ready(monkeypatch):
    called = False

    def pass_migration_check(command):
        nonlocal called
        called = True

    monkeypatch.setattr(
        runserver.BaseRunserverCommand,
        "check_migrations",
        pass_migration_check,
    )
    command = runserver.Command()

    command.check_migrations()

    assert called
