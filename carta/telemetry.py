from __future__ import annotations

import subprocess
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import DatabaseError, ProgrammingError

from accounts.services import application_setting_map

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - optional dependency during partial installs
    sentry_sdk = None

_SENTRY_CONFIG_LOCK = threading.Lock()
_SENTRY_CONFIGURED_KEY: tuple[str, float, float, str, str] | None = None
_GIT_METADATA_LOCK = threading.Lock()
_GIT_METADATA_CACHE: dict[str, str] | None = None


@dataclass(frozen=True)
class SentryTelemetryConfig:
    dsn: str
    traces_sample_rate: float
    profiles_sample_rate: float
    environment: str
    release: str


def start_sentry_transaction():
    config = configure_sentry()
    if not config:
        return None
    return sentry_sdk.start_transaction(name="carta.request", op="http.server")


def sentry_span(op: str, description: str):
    if sentry_sdk is None:
        return nullcontext()
    try:
        return sentry_sdk.start_span(op=op, description=description)
    except Exception:
        return nullcontext()


def finish_sentry_transaction(
    transaction, request, response, *, elapsed_ms: float, query_count: int
):
    if transaction is None:
        return
    route_name = _route_name(request)
    _set_sentry_transaction_name(transaction, route_name)
    _set_sentry_value(transaction, "route", route_name)
    _set_sentry_value(transaction, "method", getattr(request, "method", ""))
    _set_sentry_value(transaction, "status_code", getattr(response, "status_code", 0))
    _set_sentry_value(transaction, "elapsed_ms", round(elapsed_ms, 1))
    _set_sentry_value(transaction, "query_count", query_count)
    _set_sentry_value(transaction, "release_channel", _release_channel())


def capture_sentry_exception(exc: Exception, request, *, query_count: int) -> None:
    if not configure_sentry():
        return
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("route", _route_name(request))
        scope.set_tag("method", getattr(request, "method", ""))
        scope.set_tag("query_count", query_count)
        sentry_sdk.capture_exception(exc)


def configure_sentry() -> SentryTelemetryConfig | None:
    global _SENTRY_CONFIGURED_KEY
    config = _sentry_config()
    if not config or sentry_sdk is None:
        return None
    config_key = (
        config.dsn,
        config.traces_sample_rate,
        config.profiles_sample_rate,
        config.environment,
        config.release,
    )
    with _SENTRY_CONFIG_LOCK:
        if _SENTRY_CONFIGURED_KEY != config_key:
            sentry_sdk.init(
                dsn=config.dsn,
                traces_sample_rate=config.traces_sample_rate,
                profiles_sample_rate=config.profiles_sample_rate,
                environment=config.environment,
                release=config.release,
                send_default_pii=False,
                before_send=_scrub_sentry_event,
                before_send_transaction=_scrub_sentry_event,
            )
            git_metadata = _git_metadata()
            sentry_sdk.set_tag("release_channel", git_metadata["release_channel"])
            sentry_sdk.set_tag("git_commit", git_metadata["git_commit"])
            _SENTRY_CONFIGURED_KEY = config_key
    return config


def _sentry_config() -> SentryTelemetryConfig | None:
    try:
        settings_map = application_setting_map()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return None
    telemetry_enabled = _setting_bool(settings_map.get("telemetry_enabled", "true"))
    dsn = settings_map.get("sentry_dsn", "").strip()
    if not telemetry_enabled or not dsn:
        return None
    sample_rate = _sample_rate(settings_map.get("sentry_traces_sample_rate", "0.05"))
    profiles_sample_rate = _sample_rate(
        settings_map.get("sentry_profiles_sample_rate", "0.01"),
        default=0.01,
    )
    environment = settings_map.get("sentry_environment", "community-install").strip()
    return SentryTelemetryConfig(
        dsn=dsn,
        traces_sample_rate=sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        environment=environment or "community-install",
        release=_sentry_release(),
    )


def _route_name(request) -> str:
    resolver_match = getattr(request, "resolver_match", None)
    return getattr(resolver_match, "view_name", "") or "unknown"


def _setting_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sample_rate(value: str, *, default: float = 0.05) -> float:
    try:
        sample_rate = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(sample_rate, 0.0), 1.0)


def _sentry_release() -> str:
    return _git_metadata()["release"]


def _release_channel() -> str:
    return _git_metadata()["release_channel"]


def _git_metadata() -> dict[str, str]:
    global _GIT_METADATA_CACHE
    if _GIT_METADATA_CACHE is None:
        with _GIT_METADATA_LOCK:
            if _GIT_METADATA_CACHE is None:
                tag = _git_value(["describe", "--tags", "--exact-match"])
                commit = _git_value(["rev-parse", "--short", "HEAD"])
                branch = _git_value(["rev-parse", "--abbrev-ref", "HEAD"])
                version = tag if tag != "unknown" else commit
                _GIT_METADATA_CACHE = {
                    "git_commit": commit,
                    "release": f"carta-arcanum@{_sanitize_sentry_release(version)}",
                    "release_channel": "testing" if branch == "main" else "stable",
                }
    return _GIT_METADATA_CACHE


def _git_value(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *command],
            cwd=settings.BASE_DIR,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _sanitize_sentry_release(value: str) -> str:
    sanitized = value.replace("/", "-").replace("\\", "-").strip()
    if sanitized in {"", ".", ".."}:
        return "unknown"
    return sanitized[:180]


def _set_sentry_transaction_name(transaction, route_name: str) -> None:
    if hasattr(transaction, "set_name"):
        transaction.set_name(route_name, source="route")
    else:
        transaction.name = route_name


def _set_sentry_value(transaction, key: str, value) -> None:
    if hasattr(transaction, "set_tag"):
        transaction.set_tag(key, value)
    if hasattr(transaction, "set_data"):
        transaction.set_data(key, value)


def _scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    event.pop("user", None)
    if "request" in event:
        request = event["request"]
        method = request.get("method") if isinstance(request, dict) else None
        event["request"] = {"method": method} if method else {}
    for key in ("breadcrumbs", "extra"):
        event.pop(key, None)
    return event
