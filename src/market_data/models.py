from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class PriceInterval(StrEnum):
    ONE_DAY = "1d"


@dataclass(frozen=True, slots=True)
class Ticker:
    symbol: str

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Тикер не может быть пустым")

        object.__setattr__(self, "symbol", normalized_symbol)


@dataclass(frozen=True, slots=True)
class PriceHistoryRequest:
    ticker: Ticker
    date_from: date
    date_to: date
    interval: PriceInterval = PriceInterval.ONE_DAY

    def __post_init__(self) -> None:
        if self.date_from >= self.date_to:
            raise ValueError("Дата начала периода должна быть раньше даты окончания")


@dataclass(frozen=True, slots=True)
class PricePoint:
    trading_date: date
    adjusted_close: Decimal

    def __post_init__(self) -> None:
        if self.adjusted_close <= Decimal("0"):
            raise ValueError("Скорректированная цена должна быть больше нуля")


@dataclass(frozen=True, slots=True)
class PriceHistory:
    ticker: Ticker
    currency: str
    points: tuple[PricePoint, ...]

    def __post_init__(self) -> None:
        normalized_currency = self.currency.strip().upper()

        if not normalized_currency:
            raise ValueError("Валюта не может быть пустой")

        if not self.points:
            raise ValueError("История цен не может быть пустой")

        trading_dates = tuple(point.trading_date for point in self.points)

        if trading_dates != tuple(sorted(trading_dates)):
            raise ValueError("Точки истории должны быть упорядочены по дате")

        if len(trading_dates) != len(set(trading_dates)):
            raise ValueError("История не должна содержать повторяющиеся даты")

        object.__setattr__(
            self,
            "currency",
            normalized_currency,
        )
