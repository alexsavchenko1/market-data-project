from datetime import date
from decimal import Decimal

import httpx
import pytest

from market_data.exceptions import (
    MarketDataRequestError,
    MarketDataResponseError,
)
from market_data.models import (
    PriceHistoryRequest,
    Ticker,
)
from market_data.providers.yahoo import YahooFinanceProvider


def test_yahoo_provider_returns_price_history() -> None:
    payload: dict[str, object] = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": "AAPL",
                    },
                    "timestamp": [
                        1735689600,
                        1735776000,
                    ],
                    "indicators": {
                        "adjclose": [
                            {
                                "adjclose": [
                                    180.5,
                                    182.25,
                                ]
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v8/finance/chart/AAPL")
        assert request.url.params["interval"] == "1d"

        return httpx.Response(
            status_code=200,
            json=payload,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=(
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            "v8/finance/chart"
        ),
        transport=transport,
        timeout=10.0,
    ) as client:
        provider = YahooFinanceProvider(client)

        history = provider.fetch_history(
            PriceHistoryRequest(
                ticker=Ticker("AAPL"),
                date_from=date(2025, 1, 1),
                date_to=date(2025, 1, 3),
            )
        )

    assert history.ticker == Ticker("AAPL")
    assert history.currency == "USD"
    assert len(history.points) == 2
    assert history.points[0].trading_date == date(2025, 1, 1)
    assert history.points[0].adjusted_close == Decimal("180.5")


def test_yahoo_provider_handles_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            text="Too Many Requests",
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=(
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            "v8/finance/chart"
        ),
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataRequestError,
            match="Не удалось получить данные для AAPL",
        ):
            provider.fetch_history(
                PriceHistoryRequest(
                    ticker=Ticker("AAPL"),
                    date_from=date(2025, 1, 1),
                    date_to=date(2025, 1, 3),
                )
            )


def test_yahoo_provider_handles_empty_result() -> None:
    payload: dict[str, object] = {
        "chart": {
            "result": [],
            "error": None,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=payload,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=(
            "https://query1.finance.yahoo.com/v8/finance/chart/"
        ),
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataResponseError,
            match="не вернул данные",
        ):
            provider.fetch_history(
                PriceHistoryRequest(
                    ticker=Ticker("UNKNOWN"),
                    date_from=date(2025, 1, 1),
                    date_to=date(2025, 1, 3),
                )
            )