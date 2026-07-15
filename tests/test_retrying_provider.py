from datetime import date
from decimal import Decimal

import pytest

from market_data.exceptions import (
    MarketDataResponseError,
    MarketDataTransientError,
)
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)
from market_data.providers.retrying import (
    RetryingMarketDataProvider,
    RetryPolicy,
)


def create_request() -> PriceHistoryRequest:
    return PriceHistoryRequest(
        ticker=Ticker("AAPL"),
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 10),
    )


def create_history() -> PriceHistory:
    return PriceHistory(
        ticker=Ticker("AAPL"),
        currency="USD",
        points=(
            PricePoint(
                trading_date=date(2025, 1, 2),
                adjusted_close=Decimal("100"),
            ),
        ),
    )


class FlakyProvider:
    def __init__(self) -> None:
        self.attempts = 0

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        self.attempts += 1

        if self.attempts < 3:
            raise MarketDataTransientError("Временная тестовая ошибка")

        return create_history()


class AlwaysFailingProvider:
    def __init__(self) -> None:
        self.attempts = 0

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        self.attempts += 1

        raise MarketDataTransientError("Поставщик остаётся недоступным")


class PermanentlyFailingProvider:
    def __init__(self) -> None:
        self.attempts = 0

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        self.attempts += 1

        raise MarketDataResponseError("Некорректный ответ поставщика")


def test_retrying_provider_succeeds_after_transient_failures() -> None:
    source_provider = FlakyProvider()
    delays: list[float] = []

    provider = RetryingMarketDataProvider(
        provider=source_provider,
        policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.1,
            multiplier=2,
            max_delay_seconds=1,
        ),
        sleep_function=delays.append,
    )

    history = provider.fetch_history(create_request())

    assert history.ticker == Ticker("AAPL")
    assert source_provider.attempts == 3
    assert delays == pytest.approx([0.1, 0.2])


def test_retrying_provider_stops_after_max_attempts() -> None:
    source_provider = AlwaysFailingProvider()
    delays: list[float] = []

    provider = RetryingMarketDataProvider(
        provider=source_provider,
        policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.1,
            multiplier=2,
            max_delay_seconds=1,
        ),
        sleep_function=delays.append,
    )

    with pytest.raises(
        MarketDataTransientError,
        match="Поставщик остаётся недоступным",
    ):
        provider.fetch_history(create_request())

    assert source_provider.attempts == 3
    assert delays == pytest.approx([0.1, 0.2])


def test_retrying_provider_does_not_retry_permanent_error() -> None:
    source_provider = PermanentlyFailingProvider()
    delays: list[float] = []

    provider = RetryingMarketDataProvider(
        provider=source_provider,
        policy=RetryPolicy(),
        sleep_function=delays.append,
    )

    with pytest.raises(
        MarketDataResponseError,
        match="Некорректный ответ поставщика",
    ):
        provider.fetch_history(create_request())

    assert source_provider.attempts == 1
    assert delays == []


def test_retry_policy_limits_exponential_delay() -> None:
    policy = RetryPolicy(
        max_attempts=5,
        initial_delay_seconds=0.5,
        multiplier=3,
        max_delay_seconds=1,
    )

    assert policy.get_delay_after_failure(1) == 0.5
    assert policy.get_delay_after_failure(2) == 1
    assert policy.get_delay_after_failure(3) == 1


def test_retry_policy_rejects_invalid_attempt_count() -> None:
    with pytest.raises(
        ValueError,
        match="Количество попыток должно быть больше нуля",
    ):
        RetryPolicy(max_attempts=0)
