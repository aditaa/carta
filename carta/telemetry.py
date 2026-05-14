from __future__ import annotations

import json
import platform
import threading
import urllib.request
from typing import Any

from django import get_version
from django.conf import settings

from accounts.services import application_setting_map


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


def _telemetry_settings() -> dict[str, str | bool]:
    settings_map = application_setting_map()
    endpoint = settings_map.get("telemetry_endpoint", "").strip()
    if endpoint and not endpoint.startswith(("https://", "http://")):
        endpoint = ""
    return {
        "enabled": settings_map.get("telemetry_enabled", "true").strip().lower()
        in {"1", "true", "yes", "on"},
        "endpoint": endpoint,
    }


def _performance_payload(
    request,
    response,
    *,
    elapsed_ms: float,
    query_count: int,
) -> dict[str, Any]:
    resolver_match = getattr(request, "resolver_match", None)
    route_name = getattr(resolver_match, "view_name", "") or "unknown"
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
