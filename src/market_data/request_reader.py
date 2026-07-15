import csv
from collections.abc import Iterator, Mapping
from datetime import date
from pathlib import Path

from market_data.models import (
    PriceHistoryRequest,
    PriceInterval,
    Ticker,
)

REQUIRED_COLUMNS = {
    "symbol",
    "date_from",
    "date_to",
    "interval",
}


def _get_required_value(
    row: Mapping[str, str | None],
    column_name: str,
    row_number: int,
) -> str:
    value = row.get(column_name)

    if value is None or not value.strip():
        raise ValueError(
            f"В строке {row_number} не заполнен столбец "
            f"'{column_name}'"
        )

    return value.strip()


def generate_price_history_requests(
    file_path: Path,
) -> Iterator[PriceHistoryRequest]:
    """Последовательно читает параметры запросов из CSV-файла."""

    with file_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("Файл запросов не содержит заголовка")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)

        if missing_columns:
            formatted_columns = ", ".join(sorted(missing_columns))

            raise ValueError(
                "В файле отсутствуют обязательные столбцы: "
                f"{formatted_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            symbol = _get_required_value(
                row,
                "symbol",
                row_number,
            )
            date_from_raw = _get_required_value(
                row,
                "date_from",
                row_number,
            )
            date_to_raw = _get_required_value(
                row,
                "date_to",
                row_number,
            )
            interval_raw = _get_required_value(
                row,
                "interval",
                row_number,
            )

            try:
                date_from = date.fromisoformat(date_from_raw)
                date_to = date.fromisoformat(date_to_raw)
            except ValueError as error:
                raise ValueError(
                    f"В строке {row_number} указана некорректная дата"
                ) from error

            try:
                interval = PriceInterval(interval_raw)
            except ValueError as error:
                raise ValueError(
                    f"В строке {row_number} указан "
                    f"неподдерживаемый интервал '{interval_raw}'"
                ) from error

            try:
                yield PriceHistoryRequest(
                    ticker=Ticker(symbol),
                    date_from=date_from,
                    date_to=date_to,
                    interval=interval,
                )
            except ValueError as error:
                raise ValueError(
                    f"Некорректные параметры в строке "
                    f"{row_number}: {error}"
                ) from error