from collections.abc import Iterable
from time import perf_counter

from market_data.application.batch_result import (
    BatchFetchResult,
    FetchFailure,
)
from market_data.exceptions import MarketDataError
from market_data.models import PriceHistory, PriceHistoryRequest
from market_data.providers.base import MarketDataProvider


def fetch_histories_sequentially(
    requests: Iterable[PriceHistoryRequest],
    provider: MarketDataProvider,
) -> BatchFetchResult:
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

    return BatchFetchResult(
        histories=tuple(histories),
        failures=tuple(failures),
        elapsed_seconds=elapsed_seconds,
    )