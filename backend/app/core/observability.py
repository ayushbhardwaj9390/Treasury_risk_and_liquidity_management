from __future__ import annotations

import threading
from collections import defaultdict
from time import perf_counter

_lock = threading.Lock()
_request_count: dict[tuple[str, str, int], int] = defaultdict(int)
_request_latency_sum: dict[tuple[str, str], float] = defaultdict(float)
_request_latency_count: dict[tuple[str, str], int] = defaultdict(int)
_event_count: dict[tuple[str, str], int] = defaultdict(int)
_execution_count: dict[str, int] = defaultdict(int)


def observe_request(method: str, path: str, status: int, elapsed_seconds: float) -> None:
    key = (method, path, status)
    latency_key = (method, path)
    with _lock:
        _request_count[key] += 1
        _request_latency_sum[latency_key] += elapsed_seconds
        _request_latency_count[latency_key] += 1


def observe_treasury_event(event_type: str, processing_status: str) -> None:
    with _lock:
        _event_count[(event_type, processing_status)] += 1


def observe_execution_message(status: str) -> None:
    with _lock:
        _execution_count[status] += 1


def render_prometheus() -> str:
    lines = [
        "# HELP treasury_http_requests_total Total HTTP requests",
        "# TYPE treasury_http_requests_total counter",
    ]
    with _lock:
        for (method, path, status), value in sorted(_request_count.items()):
            safe_path = path.replace('"', '')
            lines.append(f'treasury_http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {value}')
        lines.extend([
            "# HELP treasury_http_request_latency_seconds_avg Average request latency",
            "# TYPE treasury_http_request_latency_seconds_avg gauge",
        ])
        for (method, path), total in sorted(_request_latency_sum.items()):
            count = max(_request_latency_count[(method, path)], 1)
            safe_path = path.replace('"', '')
            lines.append(f'treasury_http_request_latency_seconds_avg{{method="{method}",path="{safe_path}"}} {total / count:.6f}')
        lines.extend([
            "# HELP treasury_events_total Treasury event-ledger ingestion outcomes",
            "# TYPE treasury_events_total counter",
        ])
        for (event_type, processing_status), value in sorted(_event_count.items()):
            lines.append(f'treasury_events_total{{event_type="{event_type}",status="{processing_status}"}} {value}')
        lines.extend([
            "# HELP treasury_execution_messages_total Execution-message state transitions",
            "# TYPE treasury_execution_messages_total counter",
        ])
        for status, value in sorted(_execution_count.items()):
            lines.append(f'treasury_execution_messages_total{{status="{status}"}} {value}')
    return "\n".join(lines) + "\n"


class Timer:
    def __enter__(self):
        self.start = perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = perf_counter() - self.start
