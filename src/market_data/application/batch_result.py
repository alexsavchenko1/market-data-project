from dataclasses import dataclass

from market_data.models import PriceHistory, Ticker


@dataclass(frozen=True, slots=True)
class FetchFailure:
    ticker: Ticker
    message: str


@dataclass(frozen=True, slots=True)
class BatchFetchResult:
    histories: tuple[PriceHistory, ...]
    failures: tuple[FetchFailure, ...]
    elapsed_seconds: float
