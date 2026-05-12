from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import reverse

from installer.services import (
    DatabaseConfig,
    installer_is_locked,
    lock_installer,
    write_database_env,
)

pytestmark = pytest.mark.django_db


def database_form_data(**overrides):
    data = {
        "host": "127.0.0.1",
        "port": "3306",
        "database": "carta_arcanum",
        "test_database": "test_carta_arcanum",
        "user": "carta",
        "password": "change-me",
    }
    data.update(overrides)
    return data


def test_installer_index_shows_prerequisite_checks(client, tmp_path):
    lock_file = tmp_path / "installer.lock"

    with override_settings(INSTALLER_LOCK_FILE=lock_file):
        response = client.get(reverse("installer:index"))

    assert response.status_code == 200
    assert b"Welcome to Carta Arcanum" in response.content
    assert b"Python" in response.content
    assert b"MySQL driver" in response.content


def test_installer_index_reports_locked_state_after_lock_file_exists(client, tmp_path):
    lock_file = tmp_path / "installer.lock"
    with override_settings(INSTALLER_LOCK_FILE=lock_file):
        lock_installer()
        response = client.get(reverse("installer:index"))

    assert response.status_code == 200
    assert b"The installer is locked" in response.content


def test_database_setup_page_returns_success(client):
    response = client.get(reverse("installer:database"))

    assert response.status_code == 200
    assert b"Database setup" in response.content
    assert b"Test and save" in response.content


def test_database_setup_locks_after_lock_file_exists(client, tmp_path):
    lock_file = tmp_path / "installer.lock"
    with override_settings(INSTALLER_LOCK_FILE=lock_file):
        lock_installer()
        response = client.get(reverse("installer:database"))

    assert response.status_code == 200
    assert b"The installer is locked" in response.content
    assert b"Test and save database" not in response.content


def test_database_setup_saves_config_after_successful_connection(client, monkeypatch, tmp_path):
    env_file = tmp_path / ".env.local"
    tested_configs = []

    def fake_test_connection(config):
        tested_configs.append(config)

    monkeypatch.setattr("installer.views.test_mysql_connection", fake_test_connection)
    monkeypatch.setattr("installer.views.apply_database_config", lambda config: None)

    with override_settings(INSTALLER_ENV_FILE=env_file):
        response = client.post(reverse("installer:database"), database_form_data(password="secret"))

    assert response.status_code == 200
    assert b"Database connection saved and applied" in response.content
    assert b"Next: create superuser" in response.content
    assert tested_configs == [
        DatabaseConfig(
            host="127.0.0.1",
            port=3306,
            database="carta_arcanum",
            test_database="test_carta_arcanum",
            user="carta",
            password="secret",
        )
    ]
    assert 'MYSQL_PASSWORD="secret"' in env_file.read_text(encoding="utf-8")


def test_database_setup_does_not_save_config_after_failed_connection(
    client,
    monkeypatch,
    tmp_path,
):
    env_file = tmp_path / ".env.local"

    def fake_test_connection(config):
        raise RuntimeError("connection failed")

    monkeypatch.setattr("installer.views.test_mysql_connection", fake_test_connection)

    with override_settings(INSTALLER_ENV_FILE=env_file):
        response = client.post(reverse("installer:database"), database_form_data())

    assert response.status_code == 200
    assert b"connection failed" in response.content
    assert not env_file.exists()


def test_database_setup_rejects_line_breaks(client, monkeypatch, tmp_path):
    env_file = tmp_path / ".env.local"
    monkeypatch.setattr("installer.views.test_mysql_connection", lambda config: None)

    with override_settings(INSTALLER_ENV_FILE=env_file):
        response = client.post(
            reverse("installer:database"),
            database_form_data(host="127.0.0.1\nMYSQL_PASSWORD=bad"),
        )

    assert response.status_code == 200
    assert b"This value cannot contain line breaks" in response.content
    assert not env_file.exists()


def test_write_database_env_quotes_values(tmp_path):
    env_file = write_database_env(
        DatabaseConfig(
            host="localhost",
            port=3306,
            database="carta_arcanum",
            test_database="test_carta_arcanum",
            user="carta",
            password="secret with spaces",
        ),
        Path(tmp_path / ".env.local"),
    )

    content = env_file.read_text(encoding="utf-8")
    assert 'MYSQL_HOST="localhost"' in content
    assert 'MYSQL_PASSWORD="secret with spaces"' in content


def test_superuser_setup_saves_account_in_signed_cookie(client):
    response = client.post(
        reverse("installer:superuser"),
        {
            "email": "admin@example.test",
            "display_name": "Admin",
            "password1": "swordfish",
            "password2": "swordfish",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("installer:application")
    assert "carta_installer_superuser" in response.cookies


def test_application_setup_page_returns_success(client):
    response = client.get(reverse("installer:application"))

    assert response.status_code == 200
    assert b"App setup" in response.content
    assert b"Install and lock setup" in response.content


def test_application_setup_locks_after_lock_file_exists(client, tmp_path):
    lock_file = tmp_path / "installer.lock"
    with override_settings(INSTALLER_LOCK_FILE=lock_file):
        lock_installer()
        response = client.get(reverse("installer:application"))

    assert response.status_code == 200
    assert b"The installer is locked" in response.content
    assert b"Install and lock setup" not in response.content


def test_application_setup_runs_migrations_imports_rules_creates_admin_and_locks(
    client, monkeypatch, tmp_path
):
    calls = []
    lock_file = tmp_path / "installer.lock"

    def fake_call_command(name, *args, **kwargs):
        calls.append((name, args, kwargs))
        kwargs["stdout"].write(f"{name} completed\n")

    monkeypatch.setattr("installer.views.call_command", fake_call_command)
    client.post(
        reverse("installer:superuser"),
        {
            "email": "admin@example.test",
            "display_name": "Admin",
            "password1": "swordfish",
            "password2": "swordfish",
        },
    )

    with override_settings(INSTALLER_LOCK_FILE=lock_file):
        response = client.post(reverse("installer:application"))

    assert response.status_code == 200
    assert b"Setup completed. The installer is now locked." in response.content
    assert b"Open login page" in response.content
    assert b"migrate completed" in response.content
    assert b"import_rules completed" in response.content
    assert lock_file.exists()
    assert calls[0][0] == "migrate"
    assert calls[0][2]["no_input"] is True
    assert calls[1][0] == "import_rules"
    assert calls[1][1][0].name == "carta-arcanum-2.1.4.rules.json"
    assert calls[1][1][0].parent.name == "rules"


def test_application_setup_reports_command_failure(client, monkeypatch):
    def fake_call_command(name, *args, **kwargs):
        raise RuntimeError("setup failed")

    monkeypatch.setattr("installer.views.call_command", fake_call_command)
    client.post(
        reverse("installer:superuser"),
        {
            "email": "admin@example.test",
            "display_name": "Admin",
            "password1": "swordfish",
            "password2": "swordfish",
        },
    )

    response = client.post(reverse("installer:application"))

    assert response.status_code == 200
    assert b"setup failed" in response.content
    assert b"Setup completed" not in response.content


def test_installer_lock_stays_open_without_lock_file(tmp_path):
    with override_settings(INSTALLER_LOCK_FILE=tmp_path / "installer.lock"):
        assert not installer_is_locked()


def test_installer_lock_closes_when_lock_file_exists(tmp_path):
    with override_settings(INSTALLER_LOCK_FILE=tmp_path / "installer.lock"):
        lock_installer()
        assert installer_is_locked()
