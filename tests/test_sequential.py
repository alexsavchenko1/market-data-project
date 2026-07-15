from datetime import date
from decimal import Decimal

from market_data.application.sequential import (
    fetch_histories_sequentially,
)
from market_data.exceptions import MarketDataRequestError
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)


class StubMarketDataProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        self.calls.append(request.ticker.symbol)

        if request.ticker.symbol == "MSFT":
            raise MarketDataRequestError(
                "Тестовая ошибка поставщика"
            )

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


def test_sequential_fetch_processes_all_requests() -> None:
    provider = StubMarketDataProvider()

    requests = (
        PriceHistoryRequest(
            ticker=Ticker("AAPL"),
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 10),
        ),
        PriceHistoryRequest(
            ticker=Ticker("MSFT"),
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 10),
        ),
        PriceHistoryRequest(
            ticker=Ticker("NVDA"),
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 10),
        ),
    )

    result = fetch_histories_sequentially(
        requests=requests,
        provider=provider,
    )

    assert provider.calls == [
        "AAPL",
        "MSFT",
        "NVDA",
    ]

    assert [
        history.ticker.symbol
        for history in result.histories
    ] == [
        "AAPL",
        "NVDA",
    ]

    assert len(result.failures) == 1
    assert result.failures[0].ticker == Ticker("MSFT")
    assert result.elapsed_seconds >= 0