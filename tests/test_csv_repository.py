import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from market_data.models import (
    PriceHistory,
    PricePoint,
    Ticker,
)
from market_data.storage.csv_repository import (
    CsvPriceHistoryRepository,
)


def test_csv_repository_saves_price_history(
    tmp_path: Path,
) -> None:
    repository = CsvPriceHistoryRepository(tmp_path)

    history = PriceHistory(
        ticker=Ticker("AAPL"),
        currency="USD",
        points=(
            PricePoint(
                trading_date=date(2025, 1, 2),
                adjusted_close=Decimal("242.30"),
            ),
            PricePoint(
                trading_date=date(2025, 1, 3),
                adjusted_close=Decimal("241.81"),
            ),
        ),
    )

    repository.save(history)

    output_file = tmp_path / "AAPL.csv"

    assert output_file.exists()
    assert not (tmp_path / "AAPL.csv.tmp").exists()

    with output_file.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "date": "2025-01-02",
            "adjusted_close": "242.30",
            "currency": "USD",
        },
        {
            "date": "2025-01-03",
            "adjusted_close": "241.81",
            "currency": "USD",
        },
    ]