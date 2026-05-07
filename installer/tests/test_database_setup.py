from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import override_settings
from django.urls import reverse

from installer.services import DatabaseConfig, installer_is_locked, write_database_env

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


def test_installer_index_links_setup_steps(client):
    response = client.get(reverse("installer:index"))

    assert response.status_code == 200
    assert b"Configure database" in response.content
    assert b"Run app setup" in response.content
    assert b"Create admin" in response.content


def test_installer_index_reports_locked_state_after_user_exists(client, db):
    get_user_model().objects.create_user(
        email="admin@example.test",
        password="swordfish",
        display_name="Admin",
    )

    response = client.get(reverse("installer:index"))

    assert response.status_code == 200
    assert b"Setup is complete and the installer is locked" in response.content


def test_database_setup_page_returns_success(client):
    response = client.get(reverse("installer:database"))

    assert response.status_code == 200
    assert b"Database setup" in response.content
    assert b"Test and save" in response.content


def test_database_setup_locks_after_user_exists(client, db):
    get_user_model().objects.create_user(
        email="admin@example.test",
        password="swordfish",
        display_name="Admin",
    )

    response = client.get(reverse("installer:database"))

    assert response.status_code == 200
    assert b"The installer is locked" in response.content
    assert b"Test and save" not in response.content


def test_database_setup_saves_config_after_successful_connection(client, monkeypatch, tmp_path):
    env_file = tmp_path / ".env.local"
    tested_configs = []

    def fake_test_connection(config):
        tested_configs.append(config)

    monkeypatch.setattr("installer.views.test_mysql_connection", fake_test_connection)

    with override_settings(INSTALLER_ENV_FILE=env_file):
        response = client.post(reverse("installer:database"), database_form_data(password="secret"))

    assert response.status_code == 200
    assert b"Database connection saved" in response.content
    assert b"Continue to app setup" in response.content
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


def test_application_setup_page_returns_success(client):
    response = client.get(reverse("installer:application"))

    assert response.status_code == 200
    assert b"App setup" in response.content
    assert b"Run setup" in response.content


def test_application_setup_locks_after_user_exists(client, db):
    get_user_model().objects.create_user(
        email="admin@example.test",
        password="swordfish",
        display_name="Admin",
    )

    response = client.get(reverse("installer:application"))

    assert response.status_code == 200
    assert b"The installer is locked" in response.content
    assert b"Run setup" not in response.content


def test_application_setup_runs_migrations_and_imports_rules(client, monkeypatch):
    calls = []

    def fake_call_command(name, *args, **kwargs):
        calls.append((name, args, kwargs))
        kwargs["stdout"].write(f"{name} completed\n")

    monkeypatch.setattr("installer.views.call_command", fake_call_command)

    response = client.post(reverse("installer:application"))

    assert response.status_code == 200
    assert b"Database migrations and rules import completed" in response.content
    assert b"Create the first admin" in response.content
    assert b"migrate completed" in response.content
    assert b"import_rules completed" in response.content
    assert calls[0][0] == "migrate"
    assert calls[0][2]["no_input"] is True
    assert calls[1][0] == "import_rules"
    assert str(calls[1][1][0]).endswith("rules/carta-arcanum-2.1.4.rules.json")


def test_application_setup_reports_command_failure(client, monkeypatch):
    def fake_call_command(name, *args, **kwargs):
        raise RuntimeError("setup failed")

    monkeypatch.setattr("installer.views.call_command", fake_call_command)

    response = client.post(reverse("installer:application"))

    assert response.status_code == 200
    assert b"setup failed" in response.content
    assert b"Database migrations and rules import completed" not in response.content


def test_installer_lock_stays_open_when_database_is_not_ready(monkeypatch):
    def fake_exists():
        raise OperationalError("database unavailable")

    monkeypatch.setattr("installer.services.get_user_model", lambda: FakeUserModel(fake_exists))

    assert not installer_is_locked()


class FakeUserModel:
    def __init__(self, exists):
        self.objects = FakeManager(exists)


class FakeManager:
    def __init__(self, exists):
        self.exists = exists
