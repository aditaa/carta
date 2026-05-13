import logging
import time

from django.conf import settings
from django.db import connection

logger = logging.getLogger("carta.slow_queries")


class SlowQueryLoggingMiddleware:
    """Log queries over CARTA_SLOW_QUERY_MS during web requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        threshold_ms = getattr(settings, "CARTA_SLOW_QUERY_MS", 0)
        if threshold_ms <= 0:
            return self.get_response(request)

        def wrapper(execute, sql, params, many, context):
            start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms >= threshold_ms:
                    logger.warning(
                        "Slow query %.1f ms on %s %s: %s",
                        elapsed_ms,
                        request.method,
                        request.path,
                        sql,
                    )

        with connection.execute_wrapper(wrapper):
            return self.get_response(request)
