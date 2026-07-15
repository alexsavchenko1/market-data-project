import csv
from pathlib import Path

from market_data.models import PriceHistory


class CsvPriceHistoryRepository:
    def __init__(self, output_directory: Path) -> None:
        self._output_directory = output_directory

    def clear(self) -> int:
        """Удаляет ранее созданные CSV и временные файлы."""

        if not self._output_directory.exists():
            return 0

        generated_files = sorted(
            [
                *self._output_directory.glob("*.csv"),
                *self._output_directory.glob("*.csv.tmp"),
            ]
        )

        for generated_file in generated_files:
            generated_file.unlink()

        return len(generated_files)

    def save(self, history: PriceHistory) -> None:
        """Сохраняет историю одного тикера в отдельный CSV-файл."""

        self._output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = self._output_directory / f"{history.ticker.symbol}.csv"
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

        # Итоговый файл появляется только после завершения полной записи.
        temporary_path.replace(target_path)
