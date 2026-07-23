from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import sleep

from market_data.exceptions import MarketDataTransientError
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    Ticker,
)
from market_data.providers.base import MarketDataProvider


@dataclass(frozen=True, slots=True)
class RetryEvent:
    ticker: Ticker
    failed_attempt_number: int
    next_attempt_number: int
    delay_seconds: float
    message: str
    occurred_at: str


RetryCallback = Callable[[RetryEvent], None]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    multiplier: float = 2.0
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("Количество попыток должно быть больше нуля")

        if self.initial_delay_seconds < 0:
            raise ValueError("Начальная задержка не может быть отрицательной")

        if self.multiplier < 1:
            raise ValueError("Множитель задержки не может быть меньше единицы")

        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("Максимальная задержка не может быть меньше начальной")

    def get_delay_after_failure(
        self,
        failed_attempt_number: int,
    ) -> float:
        """Возвращает задержку после неудачной попытки."""

        if failed_attempt_number < 1:
            raise ValueError("Номер неудачной попытки должен быть больше нуля")

        calculated_delay = self.initial_delay_seconds * self.multiplier ** (
            failed_attempt_number - 1
        )

        return min(
            calculated_delay,
            self.max_delay_seconds,
        )


class RetryingMarketDataProvider:
    def __init__(
        self,
        provider: MarketDataProvider,
        policy: RetryPolicy,
        sleep_function: Callable[[float], None] = sleep,
        on_retry: RetryCallback | None = None,
        now_function: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._policy = policy
        self._sleep = sleep_function
        self._on_retry = on_retry
        self._now = now_function if now_function is not None else lambda: datetime.now(UTC)

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        """Получает данные с повторами при временных ошибках."""

        for attempt_number in range(
            1,
            self._policy.max_attempts + 1,
        ):
            try:
                return self._provider.fetch_history(request)

            except MarketDataTransientError as error:
                if attempt_number >= self._policy.max_attempts:
                    raise

                delay_seconds = self._policy.get_delay_after_failure(attempt_number)

                retry_event = RetryEvent(
                    ticker=request.ticker,
                    failed_attempt_number=(attempt_number),
                    next_attempt_number=(attempt_number + 1),
                    delay_seconds=delay_seconds,
                    message=str(error),
                    occurred_at=(self._now().isoformat()),
                )

                if self._on_retry is not None:
                    self._on_retry(retry_event)

                self._sleep(delay_seconds)

        raise RuntimeError("Недостижимое состояние механизма повторных попыток")
