import logging
import time

from django.conf import settings
from django.db import connection

from accounts.bug_reports import record_crash_for_bug_report
from carta.telemetry import (
    capture_sentry_exception,
    finish_sentry_transaction,
    send_performance_telemetry,
    sentry_span,
    start_sentry_transaction,
)

logger = logging.getLogger("carta.slow_queries")


class SlowQueryLoggingMiddleware:
    """Log queries over CARTA_SLOW_QUERY_MS during web requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        threshold_ms = getattr(settings, "CARTA_SLOW_QUERY_MS", 0)
        query_count = 0

        def wrapper(execute, sql, params, many, context):
            nonlocal query_count
            query_count += 1
            start = time.perf_counter()
            try:
                with sentry_span("db.query", "database query"):
                    return execute(sql, params, many, context)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if threshold_ms > 0 and elapsed_ms >= threshold_ms:
                    logger.warning(
                        "Slow query %.1f ms on %s %s: %s",
                        elapsed_ms,
                        request.method,
                        request.path,
                        sql,
                    )

        request_start = time.perf_counter()
        transaction = start_sentry_transaction()
        try:
            if transaction is None:
                with connection.execute_wrapper(wrapper):
                    response = self.get_response(request)
            else:
                with transaction:
                    with connection.execute_wrapper(wrapper):
                        response = self.get_response(request)
                    elapsed_ms = (time.perf_counter() - request_start) * 1000
                    finish_sentry_transaction(
                        transaction,
                        request,
                        response,
                        elapsed_ms=elapsed_ms,
                        query_count=query_count,
                    )
        except Exception as exc:
            record_crash_for_bug_report(request, exc, query_count=query_count)
            capture_sentry_exception(exc, request, query_count=query_count)
            raise
        elapsed_ms = (time.perf_counter() - request_start) * 1000
        send_performance_telemetry(
            request,
            response,
            elapsed_ms=elapsed_ms,
            query_count=query_count,
        )
        return response
