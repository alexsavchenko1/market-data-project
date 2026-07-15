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


def test_csv_repository_clears_generated_files(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "prices"
    output_directory.mkdir()

    (output_directory / "AAPL.csv").write_text(
        "test",
        encoding="utf-8",
    )
    (output_directory / "MSFT.csv.tmp").write_text(
        "test",
        encoding="utf-8",
    )
    (output_directory / ".gitkeep").write_text(
        "",
        encoding="utf-8",
    )
    (output_directory / "notes.txt").write_text(
        "Не удалять",
        encoding="utf-8",
    )

    repository = CsvPriceHistoryRepository(output_directory)

    removed_count = repository.clear()

    assert removed_count == 2
    assert not (output_directory / "AAPL.csv").exists()
    assert not (output_directory / "MSFT.csv.tmp").exists()
    assert (output_directory / ".gitkeep").exists()
    assert (output_directory / "notes.txt").exists()


def test_csv_repository_clear_accepts_missing_directory(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "missing"

    repository = CsvPriceHistoryRepository(output_directory)

    removed_count = repository.clear()

    assert removed_count == 0
    assert not output_directory.exists()
