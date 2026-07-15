from collections.abc import Iterable
from dataclasses import dataclass
from time import perf_counter

from market_data.exceptions import MarketDataError
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    Ticker,
)
from market_data.providers.base import MarketDataProvider


@dataclass(frozen=True, slots=True)
class FetchFailure:
    ticker: Ticker
    message: str


@dataclass(frozen=True, slots=True)
class SequentialFetchResult:
    histories: tuple[PriceHistory, ...]
    failures: tuple[FetchFailure, ...]
    elapsed_seconds: float


def fetch_histories_sequentially(
    requests: Iterable[PriceHistoryRequest],
    provider: MarketDataProvider,
) -> SequentialFetchResult:
    """Последовательно получает историю цен для всех запросов."""

    histories: list[PriceHistory] = []
    failures: list[FetchFailure] = []

    started_at = perf_counter()

    for request in requests:
        try:
            history = provider.fetch_history(request)
        except MarketDataError as error:
            # Ошибка одного тикера не должна останавливать весь пакет.
            failures.append(
                FetchFailure(
                    ticker=request.ticker,
                    message=str(error),
                )
            )
            continue

        histories.append(history)

    elapsed_seconds = perf_counter() - started_at

    return SequentialFetchResult(
        histories=tuple(histories),
        failures=tuple(failures),
        elapsed_seconds=elapsed_seconds,
    )