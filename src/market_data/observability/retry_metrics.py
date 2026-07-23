from threading import Lock

from market_data.observability.event_log import (
    JsonLineEventLogger,
)
from market_data.providers.retrying import RetryEvent


class RetryMetrics:
    def __init__(self) -> None:
        self._events: list[RetryEvent] = []
        self._lock = Lock()

    def reset(self) -> None:
        """Очищает метрики перед новым запуском."""

        with self._lock:
            self._events.clear()

    def record(
        self,
        event: RetryEvent,
    ) -> None:
        """Сохраняет событие повторной попытки."""

        with self._lock:
            self._events.append(event)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def events(
        self,
    ) -> tuple[RetryEvent, ...]:
        with self._lock:
            return tuple(self._events)


class RetryEventObserver:
    def __init__(
        self,
        metrics: RetryMetrics,
        event_logger: JsonLineEventLogger,
    ) -> None:
        self._metrics = metrics
        self._event_logger = event_logger

    def __call__(
        self,
        event: RetryEvent,
    ) -> None:
        """Записывает повтор в метрики и структурированный журнал."""

        self._metrics.record(event)

        self._event_logger.emit(
            event_name="retry_scheduled",
            occurred_at=event.occurred_at,
            details={
                "ticker": event.ticker.symbol,
                "failed_attempt_number": (event.failed_attempt_number),
                "next_attempt_number": (event.next_attempt_number),
                "delay_seconds": (event.delay_seconds),
                "message": event.message,
            },
        )
