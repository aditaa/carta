import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.fixture(autouse=True)
def installed_app(settings, tmp_path):
    settings.INSTALLER_LOCK_FILE = tmp_path / "installer.lock"
    settings.INSTALLER_LOCK_FILE.write_text("installed\n", encoding="utf-8")


def create_user(email: str = "denizen@example.test"):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Test Denizen",
    )


@pytest.mark.django_db
def test_login_page_returns_success(client):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert b"Sign in" in response.content
    assert b"Email" in response.content
    assert b"Create the first admin" in response.content


@pytest.mark.django_db
def test_user_can_login_with_email_and_password(client):
    user = create_user()

    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "swordfish"},
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")

    home = client.get(reverse("dashboard:home"))
    assert b"Test Denizen" in home.content
    assert b"Sign out" in home.content


@pytest.mark.django_db
def test_login_page_hides_first_admin_link_once_user_exists(client):
    create_user()

    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert b"Create the first admin" not in response.content


@pytest.mark.django_db
def test_invalid_login_stays_on_login_page(client):
    create_user()

    response = client.post(
        reverse("accounts:login"),
        {"username": "denizen@example.test", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Please enter a correct email and password" in response.content


@pytest.mark.django_db
def test_first_admin_setup_creates_superuser_and_logs_in(client):
    response = client.post(
        reverse("accounts:setup"),
        {
            "email": "admin@example.test",
            "display_name": "First Admin",
            "password1": "swordfish",
            "password2": "swordfish",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")

    user = get_user_model().objects.get(email="admin@example.test")
    assert user.is_staff
    assert user.is_superuser
    assert user.check_password("swordfish")

    home = client.get(reverse("dashboard:home"))
    assert b"First Admin" in home.content


@pytest.mark.django_db
def test_first_admin_setup_closes_after_user_exists(client):
    create_user()

    response = client.get(reverse("accounts:setup"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")


@pytest.mark.django_db
def test_logout_clears_session(client):
    user = create_user()
    client.force_login(user)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")

    home = client.get(reverse("dashboard:home"))
    assert b"Sign in" in home.content
    assert b"Test Denizen" not in home.content
