from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0


class CircuitOpenError(RuntimeError):
    pass


class ConnectorCircuitBreaker:
    """In-process reference circuit breaker for connector adapters.

    Production deployments can back this state with Redis or a service-mesh policy when
    multiple application instances must share breaker state.
    """

    def __init__(self, failure_threshold: int = 3, recovery_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at: datetime | None = None

    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def before_call(self) -> None:
        if self.state != CircuitState.OPEN:
            return
        if self.opened_at and self._now() >= self.opened_at + timedelta(seconds=self.recovery_seconds):
            self.state = CircuitState.HALF_OPEN
            return
        raise CircuitOpenError("Connector circuit is open")

    def success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = self._now()


class ResilientConnectorRunner:
    def __init__(self, breaker: ConnectorCircuitBreaker | None = None, retry: RetryPolicy | None = None):
        self.breaker = breaker or ConnectorCircuitBreaker()
        self.retry = retry or RetryPolicy()

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.breaker.before_call()
        last_error: Exception | None = None
        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                result = await operation()
                self.breaker.success()
                return result
            except Exception as exc:
                last_error = exc
                self.breaker.failure()
                if self.breaker.state == CircuitState.OPEN or attempt >= self.retry.max_attempts:
                    break
                delay = min(self.retry.base_delay_seconds * (2 ** (attempt - 1)), self.retry.max_delay_seconds)
                if delay > 0:
                    await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error
