# pyright: reportUnknownMemberType=false

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


@dataclass(frozen=True, slots=True)
class NormalizedPricePoint:
    trading_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class NormalizedPriceSeries:
    ticker: str
    points: tuple[NormalizedPricePoint, ...]


class PriceComparisonBuilder:
    REQUIRED_COLUMNS = {
        "date",
        "adjusted_close",
        "currency",
    }

    def load_and_normalize(
        self,
        input_directory: Path,
    ) -> tuple[NormalizedPriceSeries, ...]:
        """Читает сохранённые CSV-файлы и нормализует цены."""

        input_files = sorted(input_directory.glob("*.csv"))

        if not input_files:
            raise ValueError("Каталог не содержит файлов с историей цен")

        return tuple(self._load_and_normalize_file(input_file) for input_file in input_files)

    def save_chart(
        self,
        series: tuple[NormalizedPriceSeries, ...],
        output_path: Path,
    ) -> None:
        """Создаёт сравнительный график нормализованных цен."""

        if not series:
            raise ValueError("Для построения графика необходимы данные")

        figure = Figure(
            figsize=(11, 6),
            tight_layout=True,
        )

        # Используем движок, которому не требуется
        # графический интерфейс операционной системы.
        FigureCanvasAgg(figure)

        axes = figure.add_subplot(1, 1, 1)

        all_dates = sorted(
            {point.trading_date for price_series in series for point in price_series.points}
        )

        for price_series in series:
            # Порядковый номер даты является обычным числом,
            # поэтому Pyright может полностью проверить типы.
            trading_positions: list[float] = [
                float(point.trading_date.toordinal()) for point in price_series.points
            ]

            normalized_values: list[float] = [float(point.value) for point in price_series.points]

            axes.plot(
                trading_positions,
                normalized_values,
                marker="o",
                label=price_series.ticker,
            )

        tick_positions: list[float] = [
            float(trading_date.toordinal()) for trading_date in all_dates
        ]
        tick_labels: list[str] = [trading_date.isoformat() for trading_date in all_dates]

        axes.set_xticks(
            tick_positions,
            tick_labels,
            rotation=45,
            ha="right",
        )

        axes.axhline(
            y=100,
            linestyle="--",
            linewidth=1,
        )
        axes.set_title("Сравнение относительного изменения цен")
        axes.set_xlabel("Дата")
        axes.set_ylabel("Нормализованная цена, начальное значение = 100")
        axes.grid(
            visible=True,
            alpha=0.3,
        )
        axes.legend()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure.savefig(
            output_path,
            dpi=160,
        )

        figure.clear()

    def _load_and_normalize_file(
        self,
        input_file: Path,
    ) -> NormalizedPriceSeries:
        raw_points: list[tuple[date, Decimal]] = []

        with input_file.open(
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(f"Файл {input_file.name} не содержит заголовка")

            missing_columns = self.REQUIRED_COLUMNS - set(reader.fieldnames)

            if missing_columns:
                formatted_columns = ", ".join(sorted(missing_columns))

                raise ValueError(
                    f"В файле {input_file.name} отсутствуют столбцы: {formatted_columns}"
                )

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                date_raw = row.get("date")
                price_raw = row.get("adjusted_close")

                if not date_raw or not price_raw:
                    raise ValueError(
                        f"В файле {input_file.name}, строка {row_number}, отсутствует дата или цена"
                    )

                try:
                    trading_date = date.fromisoformat(date_raw)
                    adjusted_close = Decimal(price_raw)
                except (
                    ValueError,
                    InvalidOperation,
                ) as error:
                    raise ValueError(
                        f"В файле {input_file.name}, строка "
                        f"{row_number}, указаны некорректные данные"
                    ) from error

                if adjusted_close <= Decimal("0"):
                    raise ValueError(
                        f"В файле {input_file.name}, строка "
                        f"{row_number}, цена должна быть больше нуля"
                    )

                raw_points.append(
                    (
                        trading_date,
                        adjusted_close,
                    )
                )

        if not raw_points:
            raise ValueError(f"Файл {input_file.name} не содержит цен")

        raw_points.sort(key=lambda point: point[0])

        trading_dates = [trading_date for trading_date, _ in raw_points]

        if len(trading_dates) != len(set(trading_dates)):
            raise ValueError(f"Файл {input_file.name} содержит повторяющиеся даты")

        first_price = raw_points[0][1]

        normalized_points = tuple(
            NormalizedPricePoint(
                trading_date=trading_date,
                value=(adjusted_close / first_price * Decimal("100")),
            )
            for trading_date, adjusted_close in raw_points
        )

        return NormalizedPriceSeries(
            ticker=input_file.stem.upper(),
            points=normalized_points,
        )
