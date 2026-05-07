import pytest
from django.contrib.auth import get_user_model

from accounts.models import DenizenProfile


@pytest.mark.django_db
def test_user_manager_creates_email_based_user():
    user = get_user_model().objects.create_user(
        email="Denizen@Example.TEST",
        password="swordfish",
        display_name="Test Denizen",
    )

    assert user.email == "Denizen@example.test"
    assert user.display_name == "Test Denizen"
    assert user.check_password("swordfish")
    assert not hasattr(user, "username")


@pytest.mark.django_db
def test_denizen_profile_links_to_custom_user():
    user = get_user_model().objects.create_user(
        email="profile@example.test",
        password="swordfish",
        display_name="Profile Denizen",
    )

    profile = DenizenProfile.objects.create(user=user, character_name="Aster")

    assert user.denizen_profile == profile
    assert str(profile) == "Aster"
