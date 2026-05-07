from django.conf import settings


def test_custom_user_model_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"
