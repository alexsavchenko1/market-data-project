from collections.abc import Iterable
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from time import perf_counter

from market_data.application.batch_result import (
    BatchFetchResult,
    FetchFailure,
)
from market_data.exceptions import MarketDataError
from market_data.models import PriceHistory, PriceHistoryRequest
from market_data.providers.base import MarketDataProvider


def fetch_histories_concurrently(
    requests: Iterable[PriceHistoryRequest],
    provider: MarketDataProvider,
    max_workers: int,
) -> BatchFetchResult:
    """Параллельно получает историю цен через пул потоков."""

    if max_workers < 1:
        raise ValueError(
            "Количество рабочих потоков должно быть больше нуля"
        )

    indexed_requests = tuple(enumerate(requests))

    indexed_histories: list[tuple[int, PriceHistory]] = []
    indexed_failures: list[tuple[int, FetchFailure]] = []

    started_at = perf_counter()

    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="market-fetcher",
    ) as executor:
        future_to_request: dict[
            Future[PriceHistory],
            tuple[int, PriceHistoryRequest],
        ] = {
            executor.submit(
                provider.fetch_history,
                request,
            ): (request_index, request)
            for request_index, request in indexed_requests
        }

        for future in as_completed(future_to_request):
            request_index, request = future_to_request[future]

            try:
                history = future.result()
            except MarketDataError as error:
                # Ожидаемая ошибка поставщика относится
                # только к конкретному тикеру.
                indexed_failures.append(
                    (
                        request_index,
                        FetchFailure(
                            ticker=request.ticker,
                            message=str(error),
                        ),
                    )
                )
                continue

            indexed_histories.append(
                (
                    request_index,
                    history,
                )
            )

    elapsed_seconds = perf_counter() - started_at

    # Потоки завершаются в произвольном порядке.
    # Возвращаем результаты в порядке входного файла.
    indexed_histories.sort(key=lambda item: item[0])
    indexed_failures.sort(key=lambda item: item[0])

    return BatchFetchResult(
        histories=tuple(
            history
            for _, history in indexed_histories
        ),
        failures=tuple(
            failure
            for _, failure in indexed_failures
        ),
        elapsed_seconds=elapsed_seconds,
    )