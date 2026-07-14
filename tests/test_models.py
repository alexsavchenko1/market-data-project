import pytest

from market_data.models import Ticker


def test_ticker_normalizes_symbol() -> None:
    ticker = Ticker(symbol=" aapl ")

    assert ticker.symbol == "AAPL"


def test_ticker_rejects_empty_symbol() -> None:
    with pytest.raises(
        ValueError,
        match="Тикер не может быть пустым",
    ):
        Ticker(symbol="   ")