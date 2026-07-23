from decimal import Decimal
from pathlib import Path

import pytest

from market_data.analysis.comparison import (
    PriceComparisonBuilder,
)


def test_comparison_builder_normalizes_prices(
    tmp_path: Path,
) -> None:
    input_directory = tmp_path / "prices"
    input_directory.mkdir()

    price_file = input_directory / "AAPL.csv"
    price_file.write_text(
        "date,adjusted_close,currency\n"
        "2025-01-02,200,USD\n"
        "2025-01-03,220,USD\n"
        "2025-01-06,180,USD\n",
        encoding="utf-8",
    )

    builder = PriceComparisonBuilder()

    series = builder.load_and_normalize(input_directory)

    assert len(series) == 1
    assert series[0].ticker == "AAPL"

    assert [point.value for point in series[0].points] == [
        Decimal("100"),
        Decimal("110.0"),
        Decimal("90.0"),
    ]


def test_comparison_builder_loads_files_in_stable_order(
    tmp_path: Path,
) -> None:
    input_directory = tmp_path / "prices"
    input_directory.mkdir()

    for ticker in ("MSFT", "AAPL"):
        price_file = input_directory / f"{ticker}.csv"
        price_file.write_text(
            "date,adjusted_close,currency\n2025-01-02,100,USD\n",
            encoding="utf-8",
        )

    builder = PriceComparisonBuilder()

    series = builder.load_and_normalize(input_directory)

    assert [item.ticker for item in series] == [
        "AAPL",
        "MSFT",
    ]


def test_comparison_builder_creates_chart(
    tmp_path: Path,
) -> None:
    input_directory = tmp_path / "prices"
    input_directory.mkdir()

    price_file = input_directory / "AAPL.csv"
    price_file.write_text(
        "date,adjusted_close,currency\n2025-01-02,200,USD\n2025-01-03,220,USD\n",
        encoding="utf-8",
    )

    builder = PriceComparisonBuilder()
    series = builder.load_and_normalize(input_directory)

    output_path = tmp_path / "charts" / "comparison.png"

    builder.save_chart(
        series=series,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_comparison_builder_rejects_empty_directory(
    tmp_path: Path,
) -> None:
    builder = PriceComparisonBuilder()

    with pytest.raises(
        ValueError,
        match="Каталог не содержит файлов",
    ):
        builder.load_and_normalize(tmp_path)
