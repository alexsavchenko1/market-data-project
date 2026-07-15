import csv
from pathlib import Path

from market_data.models import PriceHistory


class CsvPriceHistoryRepository:
    def __init__(self, output_directory: Path) -> None:
        self._output_directory = output_directory

    def save(self, history: PriceHistory) -> None:
        """Сохраняет историю одного тикера в отдельный CSV-файл."""

        self._output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = (
            self._output_directory
            / f"{history.ticker.symbol}.csv"
        )
        temporary_path = target_path.with_suffix(".csv.tmp")

        with temporary_path.open(
            mode="w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.writer(file)

            writer.writerow(
                (
                    "date",
                    "adjusted_close",
                    "currency",
                )
            )

            for point in history.points:
                writer.writerow(
                    (
                        point.trading_date.isoformat(),
                        str(point.adjusted_close),
                        history.currency,
                    )
                )

        # Сначала полностью создаём временный файл,
        # затем атомарно заменяем итоговый.
        temporary_path.replace(target_path)