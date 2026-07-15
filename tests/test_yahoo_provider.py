from datetime import UTC, date, datetime

import httpx
import pytest

from market_data.exceptions import (
    MarketDataRequestError,
    MarketDataResponseError,
    MarketDataTransientError,
)
from market_data.models import (
    PriceHistoryRequest,
    Ticker,
)
from market_data.providers.yahoo import YahooFinanceProvider

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"


def create_request() -> PriceHistoryRequest:
    return PriceHistoryRequest(
        ticker=Ticker("AAPL"),
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 10),
    )


def create_timestamp(
    year: int,
    month: int,
    day: int,
) -> int:
    return int(
        datetime(
            year,
            month,
            day,
            tzinfo=UTC,
        ).timestamp()
    )


def create_success_payload() -> dict[str, object]:
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                    },
                    "timestamp": [
                        create_timestamp(2025, 1, 2),
                        create_timestamp(2025, 1, 3),
                        create_timestamp(2025, 1, 6),
                    ],
                    "indicators": {
                        "adjclose": [
                            {
                                "adjclose": [
                                    242.30,
                                    None,
                                    243.44,
                                ],
                            }
                        ],
                    },
                }
            ],
            "error": None,
        }
    }


def test_yahoo_provider_returns_price_history() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == ("/v8/finance/chart/AAPL")
        assert request.url.params["interval"] == "1d"

        return httpx.Response(
            status_code=200,
            json=create_success_payload(),
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)
        history = provider.fetch_history(create_request())

    assert history.ticker == Ticker("AAPL")
    assert history.currency == "USD"
    assert len(history.points) == 2
    assert history.points[0].trading_date == date(
        2025,
        1,
        2,
    )
    assert history.points[1].trading_date == date(
        2025,
        1,
        6,
    )


def test_yahoo_provider_marks_server_error_as_transient() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataTransientError,
            match="HTTP 503",
        ):
            provider.fetch_history(create_request())


def test_yahoo_provider_marks_rate_limit_as_transient() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataTransientError,
            match="HTTP 429",
        ):
            provider.fetch_history(create_request())


def test_yahoo_provider_marks_not_found_as_permanent() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=404,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataRequestError,
            match="HTTP 404",
        ) as error_info:
            provider.fetch_history(create_request())

    assert not isinstance(
        error_info.value,
        MarketDataTransientError,
    )


def test_yahoo_provider_marks_network_error_as_transient() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "Тестовая ошибка соединения",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataTransientError,
            match="Временная сетевая ошибка",
        ):
            provider.fetch_history(create_request())


def test_yahoo_provider_rejects_malformed_response() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        payload: dict[str, object] = {
            "chart": {
                "result": [],
                "error": None,
            }
        }

        return httpx.Response(
            status_code=200,
            json=payload,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url=BASE_URL,
        transport=transport,
    ) as client:
        provider = YahooFinanceProvider(client)

        with pytest.raises(
            MarketDataResponseError,
            match="не вернул данные",
        ):
            provider.fetch_history(create_request())
