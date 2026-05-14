import logging
import time

from django.conf import settings
from django.db import connection

from carta.telemetry import send_performance_telemetry

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
        with connection.execute_wrapper(wrapper):
            response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - request_start) * 1000
        send_performance_telemetry(
            request,
            response,
            elapsed_ms=elapsed_ms,
            query_count=query_count,
        )
        return response
