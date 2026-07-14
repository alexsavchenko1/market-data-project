import csv
from collections.abc import Iterator
from pathlib import Path

from market_data.models import Ticker


def generate_tickers(file_path: Path) -> Iterator[Ticker]:
    with file_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None or "symbol" not in reader.fieldnames:
            raise ValueError("Тикер файл должен содержать столбец 'symbol'")

        for row_number, row in enumerate(reader, start=2):
            symbol = row.get("symbol")

            if symbol is None or not symbol.strip():
                raise ValueError(
                    f"Символ тикера отсутствует в строке {row_number}"
                )

            yield Ticker(symbol=symbol)