from datetime import date
from decimal import Decimal

import pytest

from market_data.application.concurrent import (
    fetch_histories_concurrently,
)
from market_data.exceptions import MarketDataRequestError
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)


class StubConcurrentMarketDataProvider:
    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        if request.ticker.symbol == "MSFT":
            raise MarketDataRequestError("Тестовая ошибка поставщика")

        return PriceHistory(
            ticker=request.ticker,
            currency="USD",
            points=(
                PricePoint(
                    trading_date=date(2025, 1, 2),
                    adjusted_close=Decimal("100"),
                ),
            ),
        )


def create_request(symbol: str) -> PriceHistoryRequest:
    return PriceHistoryRequest(
        ticker=Ticker(symbol),
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 10),
    )


def test_concurrent_fetch_processes_all_requests() -> None:
    provider = StubConcurrentMarketDataProvider()

    requests = (
        create_request("AAPL"),
        create_request("MSFT"),
        create_request("NVDA"),
    )

    result = fetch_histories_concurrently(
        requests=requests,
        provider=provider,
        max_workers=3,
    )

    assert [history.ticker.symbol for history in result.histories] == [
        "AAPL",
        "NVDA",
    ]

    assert len(result.failures) == 1
    assert result.failures[0].ticker == Ticker("MSFT")
    assert result.elapsed_seconds >= 0


def test_concurrent_fetch_rejects_invalid_worker_count() -> None:
    provider = StubConcurrentMarketDataProvider()

    with pytest.raises(
        ValueError,
        match="Количество рабочих потоков должно быть больше нуля",
    ):
        fetch_histories_concurrently(
            requests=(),
            provider=provider,
            max_workers=0,
        )


def test_concurrent_fetch_passes_successful_histories_to_callback() -> None:
    provider = StubConcurrentMarketDataProvider()
    received_histories: list[PriceHistory] = []

    requests = (
        create_request("AAPL"),
        create_request("MSFT"),
        create_request("NVDA"),
    )

    fetch_histories_concurrently(
        requests=requests,
        provider=provider,
        max_workers=3,
        on_history_fetched=received_histories.append,
    )

    received_symbols = sorted(history.ticker.symbol for history in received_histories)

    assert received_symbols == [
        "AAPL",
        "NVDA",
    ]


# MSFT отсутствует, потому что тестовый поставщик возвращает для него ошибку
