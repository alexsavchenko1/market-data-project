from pathlib import Path

import pytest

from market_data.models import Ticker
from market_data.ticker_reader import generate_tickers


def test_generate_tickers_returns_normalized_tickers(
    tmp_path: Path,
) -> None:
    ticker_file = tmp_path / "tickers.csv"
    ticker_file.write_text(
        "symbol\n"
        "aapl\n"
        " msft \n",
        encoding="utf-8",
    )

    result = list(generate_tickers(ticker_file))

    assert result == [
        Ticker(symbol="AAPL"),
        Ticker(symbol="MSFT"),
    ]


def test_generate_tickers_rejects_missing_symbol_column(
    tmp_path: Path,
) -> None:
    ticker_file = tmp_path / "tickers.csv"
    ticker_file.write_text(
        "ticker\n"
        "AAPL\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Тикер файл должен содержать столбец 'symbol'",
    ):
        list(generate_tickers(ticker_file))


def test_generate_tickers_rejects_empty_symbol(
    tmp_path: Path,
) -> None:
    ticker_file = tmp_path / "tickers.csv"
    ticker_file.write_text(
        "symbol\n"
        "AAPL\n"
        "   \n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Символ тикера отсутствует в строке 3",
    ):
        list(generate_tickers(ticker_file))