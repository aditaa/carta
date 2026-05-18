from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class Window:
    label: str
    start: datetime
    end: datetime


def iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_count(value: Any) -> str:
    if value in (None, ""):
        return "0"
    return f"{int(round(float(value))):,}"


def format_ms(value: Any) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value):.1f} ms"


def pct_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return ((current - previous) / previous) * 100.0


class SentryClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("SENTRY_BASE_URL", "https://sentry.io").rstrip("/")
        self.org = os.environ["SENTRY_ORG"]
        self.project_slug = os.environ["SENTRY_PROJECT"]
        self.token = os.environ["SENTRY_AUTH_TOKEN"]
        self.project_id = self._project_id()

    def _request(self, path: str, params: list[tuple[str, str]] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def _project_id(self) -> str:
        data = self._request(f"/api/0/organizations/{self.org}/projects/")
        for item in data:
            if item.get("slug") == self.project_slug:
                return str(item["id"])
        raise RuntimeError(
            f"Could not resolve project id for org={self.org!r} project={self.project_slug!r}."
        )

    def issues(self, window: Window, query: str) -> list[dict[str, Any]]:
        params = [
            ("query", query),
            ("start", iso_z(window.start)),
            ("end", iso_z(window.end)),
            ("per_page", "20"),
        ]
        return self._request(
            f"/api/0/projects/{self.org}/{self.project_slug}/issues/",
            params,
        )

    def events(
        self,
        window: Window,
        *,
        dataset: str,
        fields: list[str],
        query: str = "",
        sort: str = "-count",
        limit: int = 10,
    ) -> dict[str, Any]:
        params = [
            ("project", self.project_id),
            ("dataset", dataset),
            ("start", iso_z(window.start)),
            ("end", iso_z(window.end)),
            ("sort", sort),
            ("per_page", str(limit)),
        ]
        for field in fields:
            params.append(("field", field))
        if query:
            params.append(("query", query))
        return self._request(f"/api/0/organizations/{self.org}/events/", params)

    def issues_dashboard_url(self) -> str:
        query = urllib.parse.quote("is:unresolved")
        return (
            f"{self.base_url}/organizations/{self.org}/issues/"
            f"?project={self.project_id}&query={query}"
        )

    def traces_dashboard_url(self) -> str:
        return (
            f"{self.base_url}/organizations/{self.org}/explore/traces/"
            f"?project={self.project_id}&statsPeriod=7d"
        )


def top_routes(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    rows = payload.get("data", [])
    results: dict[str, dict[str, float]] = {}
    for row in rows:
        transaction = row.get("transaction")
        if not transaction:
            continue
        results[str(transaction)] = {
            "count": float(row.get("count()", 0) or 0),
            "p95": float(row.get("p95()", 0) or 0),
            "p99": float(row.get("p99()", 0) or 0),
        }
    return results


def top_db_routes(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    rows = payload.get("data", [])
    results: dict[str, dict[str, float]] = {}
    for row in rows:
        transaction = row.get("transaction")
        if not transaction:
            continue
        results[str(transaction)] = {
            "count": float(row.get("count()", 0) or 0),
            "p95": float(row.get("p95(span.duration)", 0) or 0),
        }
    return results


def find_regressions(
    current: dict[str, dict[str, float]],
    previous: dict[str, dict[str, float]],
    *,
    latency_key: str,
    min_current_count: float,
) -> list[str]:
    findings: list[tuple[float, str]] = []
    for route, current_values in current.items():
        current_count = current_values.get("count", 0)
        previous_values = previous.get(route)
        if not previous_values or current_count < min_current_count:
            continue
        current_latency = current_values.get(latency_key, 0)
        previous_latency = previous_values.get(latency_key, 0)
        delta = pct_change(current_latency, previous_latency)
        if delta is None:
            continue
        count_delta = pct_change(current_count, previous_values.get("count", 0))
        if delta >= 30 and current_latency - previous_latency >= 20:
            findings.append(
                (
                    delta,
                    (
                        f"`{route}` {latency_key} rose to {format_ms(current_latency)} "
                        f"from {format_ms(previous_latency)}"
                        + (
                            f" ({delta:+.0f}%; volume {count_delta:+.0f}%)"
                            if count_delta is not None
                            else f" ({delta:+.0f}%)"
                        )
                    ),
                )
            )
    findings.sort(reverse=True)
    return [item[1] for item in findings[:3]]


def find_new_issues(issues: list[dict[str, Any]], window: Window) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for issue in issues:
        first_seen = parse_dt(issue.get("firstSeen"))
        if first_seen and first_seen >= window.start:
            results.append(issue)
    return results


def summarize_issue(issue: dict[str, Any]) -> str:
    short_id = issue.get("shortId") or issue.get("id") or "issue"
    title = issue.get("title") or "Untitled issue"
    count = format_count(issue.get("count"))
    last_seen = issue.get("lastSeen") or "unknown"
    permalink = issue.get("permalink")
    suffix = f" ([link]({permalink}))" if permalink else ""
    return f"`{short_id}` {title} ({count} events, last seen {last_seen}){suffix}"


def summarize_group_counts(rows: list[dict[str, Any]], key: str, *, blank_label: str) -> list[str]:
    lines: list[str] = []
    for row in rows:
        label = str(row.get(key) or blank_label)
        lines.append(f"`{label}` {format_count(row.get('count()'))}")
    return lines


def main() -> int:
    now = datetime.now(UTC)
    current = Window("current", now - timedelta(days=7), now)
    previous = Window("previous", now - timedelta(days=14), now - timedelta(days=7))
    client = SentryClient()

    unresolved = client.issues(current, "is:unresolved")
    new_issues = find_new_issues(unresolved, current)

    current_routes = client.events(
        current,
        dataset="transactions",
        fields=["transaction", "count()", "p95()", "p99()"],
        limit=10,
    )
    previous_routes = client.events(
        previous,
        dataset="transactions",
        fields=["transaction", "count()", "p95()", "p99()"],
        limit=20,
    )
    current_db = client.events(
        current,
        dataset="spans",
        fields=["transaction", "count()", "p95(span.duration)"],
        query="span.op:db",
        limit=10,
    )
    previous_db = client.events(
        previous,
        dataset="spans",
        fields=["transaction", "count()", "p95(span.duration)"],
        query="span.op:db",
        limit=20,
    )
    releases = client.events(
        current,
        dataset="transactions",
        fields=["release", "count()"],
        limit=8,
    )
    release_channels = client.events(
        current,
        dataset="transactions",
        fields=["release_channel", "count()"],
        limit=8,
    )

    current_routes_map = top_routes(current_routes)
    previous_routes_map = top_routes(previous_routes)
    current_db_map = top_db_routes(current_db)
    previous_db_map = top_db_routes(previous_db)

    route_regressions = find_regressions(
        current_routes_map,
        previous_routes_map,
        latency_key="p95",
        min_current_count=5,
    )
    db_regressions = find_regressions(
        current_db_map,
        previous_db_map,
        latency_key="p95",
        min_current_count=100,
    )

    lines = [
        "# Weekly Sentry Review",
        "",
        f"Window: {current.start.date()} to {current.end.date()} UTC",
        f"Comparison: {previous.start.date()} to {previous.end.date()} UTC",
        "",
        "## Issues",
    ]
    if unresolved:
        issues_dashboard_url = client.issues_dashboard_url()
        lines.append(
            f"- {len(unresolved)} unresolved issues in the last 7 days. "
            f"[Issues dashboard]({issues_dashboard_url})"
        )
        for issue in unresolved[:5]:
            lines.append(f"- {summarize_issue(issue)}")
    else:
        issues_dashboard_url = client.issues_dashboard_url()
        lines.append(
            f"- No unresolved issues in the last 7 days. [Issues dashboard]({issues_dashboard_url})"
        )

    if new_issues:
        lines.append(f"- {len(new_issues)} of those issues first appeared during this window.")
    else:
        lines.append("- No newly seen unresolved issues in this window.")

    lines.extend(
        [
            "",
            "## Route Volume And Latency",
            f"- [Traces dashboard]({client.traces_dashboard_url()})",
        ]
    )
    for row in current_routes.get("data", [])[:5]:
        lines.append(
            "- "
            f"`{row.get('transaction')}` {format_count(row.get('count()'))} tx, "
            f"p95 {format_ms(row.get('p95()'))}, p99 {format_ms(row.get('p99()'))}"
        )

    lines.extend(["", "## Database Spans"])
    for row in current_db.get("data", [])[:5]:
        lines.append(
            "- "
            f"`{row.get('transaction')}` {format_count(row.get('count()'))} db spans, "
            f"p95 {format_ms(row.get('p95(span.duration)'))}"
        )

    lines.extend(["", "## Releases"])
    lines.append(
        "- Top releases: "
        + "; ".join(
            summarize_group_counts(releases.get("data", [])[:5], "release", blank_label="unknown")
        )
    )
    lines.append(
        "- Release channels: "
        + "; ".join(
            summarize_group_counts(
                release_channels.get("data", [])[:5],
                "release_channel",
                blank_label="unlabeled",
            )
        )
    )

    lines.extend(["", "## Regressions"])
    if route_regressions or db_regressions:
        for item in route_regressions:
            lines.append(f"- Route latency regression: {item}")
        for item in db_regressions:
            lines.append(f"- DB span regression: {item}")
    else:
        lines.append(
            "- No notable route or database latency regressions versus the previous 7-day window."
        )

    recommendations: list[str] = []
    if unresolved:
        recommendations.append(
            "Triage unresolved issues first and confirm whether any should be "
            "escalated into code fixes this week."
        )
    if any((row.get("release_channel") or "") == "" for row in release_channels.get("data", [])):
        recommendations.append(
            "Normalize release tagging so more events carry the `release_channel` "
            "tag; unlabeled traffic is still present."
        )
    if route_regressions:
        recommendations.append(
            "Review the regressed routes in Sentry traces and compare recent code "
            "or data-shape changes before the next release."
        )
    if db_regressions:
        recommendations.append(
            "Inspect the slowest database-heavy routes for query count growth or missing indexes."
        )
    if not recommendations:
        recommendations.append(
            "No urgent follow-up from this window; keep watching for first "
            "unresolved issues and unlabeled releases."
        )

    lines.extend(["", "## Recommended Follow-Up"])
    for item in recommendations[:4]:
        lines.append(f"- {item}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyError as exc:
        print(f"Missing required environment variable: {exc.args[0]}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - automation guardrail
        print(f"Weekly Sentry review failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
