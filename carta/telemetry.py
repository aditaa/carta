from __future__ import annotations

import json
import platform
import threading
import urllib.request
from dataclasses import dataclass
from typing import Any

from django import get_version
from django.conf import settings
from django.db import DatabaseError, ProgrammingError

from accounts.services import application_setting_map

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - optional dependency during partial installs
    sentry_sdk = None

_SENTRY_CONFIG_LOCK = threading.Lock()
_SENTRY_CONFIGURED_KEY: tuple[str, float, str] | None = None


@dataclass(frozen=True)
class SentryTelemetryConfig:
    dsn: str
    traces_sample_rate: float
    environment: str


def send_performance_telemetry(request, response, *, elapsed_ms: float, query_count: int) -> None:
    telemetry_settings = _telemetry_settings()
    if not telemetry_settings["enabled"] or not telemetry_settings["endpoint"]:
        return

    payload = _performance_payload(
        request, response, elapsed_ms=elapsed_ms, query_count=query_count
    )
    thread = threading.Thread(
        target=_post_payload,
        args=(telemetry_settings["endpoint"], payload),
        daemon=True,
    )
    thread.start()


def start_sentry_transaction():
    config = configure_sentry()
    if not config:
        return None
    return sentry_sdk.start_transaction(name="carta.request", op="http.server")


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
    config_key = (config.dsn, config.traces_sample_rate, config.environment)
    with _SENTRY_CONFIG_LOCK:
        if _SENTRY_CONFIGURED_KEY != config_key:
            sentry_sdk.init(
                dsn=config.dsn,
                traces_sample_rate=config.traces_sample_rate,
                environment=config.environment,
                send_default_pii=False,
                before_send=_scrub_sentry_event,
                before_send_transaction=_scrub_sentry_event,
            )
            _SENTRY_CONFIGURED_KEY = config_key
    return config


def _sentry_config() -> SentryTelemetryConfig | None:
    try:
        settings_map = application_setting_map()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return None
    telemetry_enabled = _setting_bool(settings_map.get("telemetry_enabled", "true"))
    sentry_enabled = _setting_bool(settings_map.get("sentry_enabled", "true"))
    dsn = settings_map.get("sentry_dsn", "").strip()
    if not telemetry_enabled or not sentry_enabled or not dsn:
        return None
    sample_rate = _sample_rate(settings_map.get("sentry_traces_sample_rate", "0.05"))
    environment = settings_map.get("sentry_environment", "community-install").strip()
    return SentryTelemetryConfig(
        dsn=dsn,
        traces_sample_rate=sample_rate,
        environment=environment or "community-install",
    )


def _telemetry_settings() -> dict[str, str | bool]:
    try:
        settings_map = application_setting_map()
    except (DatabaseError, ProgrammingError, RuntimeError):
        return {"enabled": False, "endpoint": ""}
    endpoint = settings_map.get("telemetry_endpoint", "").strip()
    if endpoint and not endpoint.startswith(("https://", "http://")):
        endpoint = ""
    return {
        "enabled": _setting_bool(settings_map.get("telemetry_enabled", "true")),
        "endpoint": endpoint,
    }


def _performance_payload(
    request,
    response,
    *,
    elapsed_ms: float,
    query_count: int,
) -> dict[str, Any]:
    route_name = _route_name(request)
    return {
        "schema": "carta.performance.v1",
        "app": "carta-arcanum",
        "version": {
            "django": get_version(),
            "python": platform.python_version(),
        },
        "request": {
            "route": route_name,
            "method": getattr(request, "method", ""),
            "status_code": getattr(response, "status_code", 0),
            "elapsed_ms": round(elapsed_ms, 1),
            "query_count": query_count,
        },
        "deployment": {
            "debug": bool(settings.DEBUG),
            "database_engine": settings.DATABASES["default"]["ENGINE"],
        },
    }


def _post_payload(endpoint: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Carta-Arcanum-Telemetry",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2)
    except OSError:
        return


def _route_name(request) -> str:
    resolver_match = getattr(request, "resolver_match", None)
    return getattr(resolver_match, "view_name", "") or "unknown"


def _setting_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sample_rate(value: str) -> float:
    try:
        sample_rate = float(value)
    except (TypeError, ValueError):
        return 0.05
    return min(max(sample_rate, 0.0), 1.0)


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
