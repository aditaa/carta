import os
import shlex
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INITIAL_ENV_KEYS = set(os.environ)


def load_env_file(path: Path, *, protected_keys: set[str]) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in protected_keys:
            continue
        os.environ[key] = _parse_env_value(value.strip())


def _parse_env_value(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = shlex.split(value, comments=False, posix=True)
    except ValueError:
        return value
    if len(parsed) == 1:
        return parsed[0]
    return value


load_env_file(BASE_DIR / ".env", protected_keys=INITIAL_ENV_KEYS)
load_env_file(BASE_DIR / ".env.local", protected_keys=INITIAL_ENV_KEYS)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
CARTA_SLOW_QUERY_MS = int(os.getenv("CARTA_SLOW_QUERY_MS", "0"))
INSTALLER_ENV_FILE = Path(os.getenv("CARTA_INSTALLER_ENV_FILE", BASE_DIR / ".env.local"))
INSTALLER_LOCK_FILE = Path(os.getenv("CARTA_INSTALLER_LOCK_FILE", BASE_DIR / "installer.lock"))
CURRENT_RULES_FILE = Path(
    os.getenv(
        "CARTA_CURRENT_RULES_FILE",
        BASE_DIR / "rules" / "carta-arcanum-2.1.4.rules.json",
    )
)

INSTALLED_APPS = [
    "accounts",
    "dashboard",
    "installer",
    "rulesets",
    "resources",
    "ownership",
    "holdings",
    "buildings",
    "campaign_map",
    "transports",
    "production",
    "progression",
    "solver",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "carta.middleware.SlowQueryLoggingMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "carta.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.application_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "carta.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "carta_arcanum"),
        "USER": os.getenv("MYSQL_USER", "carta"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "change-me"),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
        "TEST": {
            "NAME": os.getenv("MYSQL_TEST_DATABASE", "test_carta_arcanum"),
        },
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "dashboard:home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
