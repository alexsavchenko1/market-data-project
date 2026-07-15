from pathlib import Path

import httpx

from market_data.application.background_writer import (
    BackgroundHistoryWriter,
)
from market_data.application.concurrent import (
    fetch_histories_concurrently,
)
from market_data.providers.yahoo import YahooFinanceProvider
from market_data.request_reader import (
    generate_price_history_requests,
)
from market_data.storage.csv_repository import (
    CsvPriceHistoryRepository,
)

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"

REQUEST_FILE = Path("config/requests.csv")
OUTPUT_DIRECTORY = Path("data/prices")

MAX_WORKERS = 5
MAX_QUEUE_SIZE = 2


def main() -> None:
    requests = tuple(
        generate_price_history_requests(REQUEST_FILE)
    )

    if not requests:
        raise SystemExit("Файл не содержит запросов")

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    repository = CsvPriceHistoryRepository(
        output_directory=OUTPUT_DIRECTORY,
    )
    writer = BackgroundHistoryWriter(
        repository=repository,
        max_queue_size=MAX_QUEUE_SIZE,
    )

    writer.start()

    try:
        with httpx.Client(
            base_url=YAHOO_BASE_URL,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "market-data-project/0.1",
            },
        ) as client:
            provider = YahooFinanceProvider(client)

            result = fetch_histories_concurrently(
                requests=requests,
                provider=provider,
                max_workers=MAX_WORKERS,
                on_history_fetched=writer.submit,
            )
    finally:
        # Дожидаемся сохранения всех элементов очереди
        # даже при неожиданной ошибке загрузки.
        writer.close()

    print("Результаты многопоточной загрузки и записи")
    print("=" * 50)
    print(f"Рабочих потоков загрузки: {MAX_WORKERS}")
    print(f"Максимальный размер очереди: {MAX_QUEUE_SIZE}")

    for history in result.histories:
        print(
            f"[ЗАГРУЖЕНО] {history.ticker.symbol}: "
            f"{len(history.points)} точек"
        )

    for failure in result.failures:
        print(
            f"[ОШИБКА ЗАГРУЗКИ] {failure.ticker.symbol}: "
            f"{failure.message}"
        )

    for failure in writer.failures:
        print(
            f"[ОШИБКА ЗАПИСИ] {failure.ticker.symbol}: "
            f"{failure.message}"
        )

    print("=" * 50)
    print(f"Загружено историй: {len(result.histories)}")
    print(f"Сохранено файлов: {writer.saved_count}")
    print(f"Ошибок загрузки: {len(result.failures)}")
    print(f"Ошибок записи: {len(writer.failures)}")
    print(f"Время загрузки: {result.elapsed_seconds:.3f} секунд")
    print(f"Каталог результатов: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()