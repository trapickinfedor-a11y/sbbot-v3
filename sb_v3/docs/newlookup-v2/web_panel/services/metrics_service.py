"""
Prometheus-compatible metrics middleware.
Exposes /metrics endpoint with:
- http_requests_total (counter)
- http_request_duration_seconds (histogram)
- http_errors_total (counter by status code)
- db_pool_size / db_pool_checked_out (gauges)
- scheduler_job_duration_seconds (histogram)
"""

import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

logger = logging.getLogger(__name__)

# In-memory counters (lightweight, no external deps)
_request_count: int = 0
_error_counts: dict[int, int] = {}
_latency_sum: float = 0.0
_latency_count: int = 0
_latency_buckets: dict[str, int] = {
    "0.01": 0, "0.05": 0, "0.1": 0, "0.25": 0,
    "0.5": 0, "1.0": 0, "2.5": 0, "5.0": 0, "10.0": 0,
}
_job_durations: dict[str, list[float]] = {}


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _request_count, _latency_sum, _latency_count

        start = time.perf_counter()
        response: Optional[Response] = None
        try:
            response = await call_next(request)
        except Exception:
            _error_counts[500] = _error_counts.get(500, 0) + 1
            raise
        finally:
            elapsed = time.perf_counter() - start
            _request_count += 1
            _latency_sum += elapsed
            _latency_count += 1

            for bucket_str in _latency_buckets:
                if elapsed <= float(bucket_str):
                    _latency_buckets[bucket_str] += 1

            if response and response.status_code >= 400:
                code = response.status_code
                _error_counts[code] = _error_counts.get(code, 0) + 1

        return response


def record_job_duration(job_name: str, duration: float):
    """Записать длительность выполнения scheduler job."""
    if job_name not in _job_durations:
        _job_durations[job_name] = []
    _job_durations[job_name].append(duration)
    if len(_job_durations[job_name]) > 100:
        _job_durations[job_name] = _job_durations[job_name][-100:]


def get_metrics_text(engine=None) -> str:
    """Генерирует текст в формате Prometheus exposition."""
    lines: list[str] = []

    # Request counter
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    lines.append(f"http_requests_total {_request_count}")

    # Error counters
    lines.append("# HELP http_errors_total HTTP errors by status code")
    lines.append("# TYPE http_errors_total counter")
    for code, count in sorted(_error_counts.items()):
        lines.append(f'http_errors_total{{status="{code}"}} {count}')

    # Latency histogram
    lines.append("# HELP http_request_duration_seconds Request latency")
    lines.append("# TYPE http_request_duration_seconds histogram")
    for bucket_str, count in _latency_buckets.items():
        lines.append(f'http_request_duration_seconds_bucket{{le="{bucket_str}"}} {count}')
    lines.append(f'http_request_duration_seconds_bucket{{le="+Inf"}} {_latency_count}')
    lines.append(f"http_request_duration_seconds_sum {_latency_sum:.6f}")
    lines.append(f"http_request_duration_seconds_count {_latency_count}")

    # DB pool (if available)
    if engine is not None:
        try:
            pool = engine.pool
            lines.append("# HELP db_pool_size Current pool size")
            lines.append("# TYPE db_pool_size gauge")
            lines.append(f"db_pool_size {pool.size()}")
            lines.append("# HELP db_pool_checked_out Connections currently in use")
            lines.append("# TYPE db_pool_checked_out gauge")
            lines.append(f"db_pool_checked_out {pool.checkedout()}")
            lines.append("# HELP db_pool_overflow Overflow connections")
            lines.append("# TYPE db_pool_overflow gauge")
            lines.append(f"db_pool_overflow {pool.overflow()}")
        except Exception:
            pass

    # Job durations
    if _job_durations:
        lines.append("# HELP scheduler_job_last_duration_seconds Last job duration")
        lines.append("# TYPE scheduler_job_last_duration_seconds gauge")
        for job_name, durations in _job_durations.items():
            if durations:
                lines.append(f'scheduler_job_last_duration_seconds{{job="{job_name}"}} {durations[-1]:.6f}')

    return "\n".join(lines) + "\n"
