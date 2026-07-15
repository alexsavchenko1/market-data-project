from datetime import date
from decimal import Decimal

import pytest

from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)


def test_price_history_request_rejects_invalid_period() -> None:
    with pytest.raises(
        ValueError,
        match="Дата начала периода должна быть раньше",
    ):
        PriceHistoryRequest(
            ticker=Ticker("AAPL"),
            date_from=date(2026, 1, 10),
            date_to=date(2026, 1, 1),
        )


def test_price_point_rejects_non_positive_price() -> None:
    with pytest.raises(
        ValueError,
        match="цена должна быть больше нуля",
    ):
        PricePoint(
            trading_date=date(2026, 1, 1),
            adjusted_close=Decimal("0"),
        )


def test_price_history_normalizes_currency() -> None:
    history = PriceHistory(
        ticker=Ticker("AAPL"),
        currency=" usd ",
        points=(
            PricePoint(
                trading_date=date(2026, 1, 1),
                adjusted_close=Decimal("180.50"),
            ),
        ),
    )

    assert history.currency == "USD"


def test_price_history_rejects_empty_points() -> None:
    with pytest.raises(
        ValueError,
        match="История цен не может быть пустой",
    ):
        PriceHistory(
            ticker=Ticker("AAPL"),
            currency="USD",
            points=(),
        )


def test_price_history_rejects_unsorted_points() -> None:
    with pytest.raises(
        ValueError,
        match="упорядочены по дате",
    ):
        PriceHistory(
            ticker=Ticker("AAPL"),
            currency="USD",
            points=(
                PricePoint(
                    trading_date=date(2026, 1, 2),
                    adjusted_close=Decimal("182"),
                ),
                PricePoint(
                    trading_date=date(2026, 1, 1),
                    adjusted_close=Decimal("180"),
                ),
            ),
        )


def test_price_history_rejects_duplicate_dates() -> None:
    with pytest.raises(
        ValueError,
        match="повторяющиеся даты",
    ):
        PriceHistory(
            ticker=Ticker("AAPL"),
            currency="USD",
            points=(
                PricePoint(
                    trading_date=date(2026, 1, 1),
                    adjusted_close=Decimal("180"),
                ),
                PricePoint(
                    trading_date=date(2026, 1, 1),
                    adjusted_close=Decimal("181"),
                ),
            ),
        )
