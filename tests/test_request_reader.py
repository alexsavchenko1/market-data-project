from datetime import date
from pathlib import Path

import pytest

from market_data.models import PriceInterval, Ticker
from market_data.request_reader import (
    generate_price_history_requests,
)


def test_generate_requests_returns_parsed_requests(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "requests.csv"
    request_file.write_text(
        "symbol,date_from,date_to,interval\n"
        " aapl ,2025-01-01,2025-01-10,1d\n"
        "msft,2025-02-01,2025-02-15,1d\n",
        encoding="utf-8",
    )

    requests = list(
        generate_price_history_requests(request_file)
    )

    assert len(requests) == 2
    assert requests[0].ticker == Ticker("AAPL")
    assert requests[0].date_from == date(2025, 1, 1)
    assert requests[0].date_to == date(2025, 1, 10)
    assert requests[0].interval == PriceInterval.ONE_DAY
    assert requests[1].ticker == Ticker("MSFT")


def test_generate_requests_rejects_missing_column(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "requests.csv"
    request_file.write_text(
        "symbol,date_from,date_to\n"
        "AAPL,2025-01-01,2025-01-10\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="отсутствуют обязательные столбцы: interval",
    ):
        list(generate_price_history_requests(request_file))


def test_generate_requests_rejects_invalid_date(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "requests.csv"
    request_file.write_text(
        "symbol,date_from,date_to,interval\n"
        "AAPL,не-дата,2025-01-10,1d\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="В строке 2 указана некорректная дата",
    ):
        list(generate_price_history_requests(request_file))


def test_generate_requests_rejects_unsupported_interval(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "requests.csv"
    request_file.write_text(
        "symbol,date_from,date_to,interval\n"
        "AAPL,2025-01-01,2025-01-10,5m\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="неподдерживаемый интервал '5m'",
    ):
        list(generate_price_history_requests(request_file))


def test_generate_requests_rejects_invalid_period(
    tmp_path: Path,
) -> None:
    request_file = tmp_path / "requests.csv"
    request_file.write_text(
        "symbol,date_from,date_to,interval\n"
        "AAPL,2025-01-10,2025-01-01,1d\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Некорректные параметры в строке 2",
    ):
        list(generate_price_history_requests(request_file))