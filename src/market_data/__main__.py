from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from market_data.analysis.comparison import (
    PriceComparisonBuilder,
)
from market_data.application.background_writer import (
    BackgroundHistoryWriter,
)
from market_data.application.concurrent import (
    fetch_histories_concurrently,
)
from market_data.observability.run_report import (
    FailureRecord,
    JsonRunReportRepository,
    RunReport,
)
from market_data.providers.retrying import (
    RetryingMarketDataProvider,
    RetryPolicy,
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
COMPARISON_CHART = Path("data/charts/comparison.png")
RUN_REPORT_PATH = Path("data/reports/latest.json")

MAX_WORKERS = 5
MAX_QUEUE_SIZE = 2

MAX_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 0.25
RETRY_DELAY_MULTIPLIER = 2.0
MAX_RETRY_DELAY_SECONDS = 2.0


def main() -> None:
    run_id = str(uuid4())
    started_at = datetime.now(UTC)

    requests = tuple(generate_price_history_requests(REQUEST_FILE))

    if not requests:
        raise SystemExit("Файл не содержит запросов")

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    repository = CsvPriceHistoryRepository(
        output_directory=OUTPUT_DIRECTORY,
    )

    removed_price_files = repository.clear()

    # Старый график не должен оставаться после неуспешного запуска.
    COMPARISON_CHART.unlink(missing_ok=True)

    writer = BackgroundHistoryWriter(
        repository=repository,
        max_queue_size=MAX_QUEUE_SIZE,
    )

    retry_policy = RetryPolicy(
        max_attempts=MAX_ATTEMPTS,
        initial_delay_seconds=(INITIAL_RETRY_DELAY_SECONDS),
        multiplier=RETRY_DELAY_MULTIPLIER,
        max_delay_seconds=MAX_RETRY_DELAY_SECONDS,
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
            yahoo_provider = YahooFinanceProvider(client)

            provider = RetryingMarketDataProvider(
                provider=yahoo_provider,
                policy=retry_policy,
            )

            result = fetch_histories_concurrently(
                requests=requests,
                provider=provider,
                max_workers=MAX_WORKERS,
                on_history_fetched=writer.submit,
            )
    finally:
        writer.close()

    chart_created = False

    if writer.saved_count > 0:
        comparison_builder = PriceComparisonBuilder()

        normalized_series = comparison_builder.load_and_normalize(OUTPUT_DIRECTORY)

        comparison_builder.save_chart(
            series=normalized_series,
            output_path=COMPARISON_CHART,
        )

        chart_created = True

    finished_at = datetime.now(UTC)

    run_report = RunReport(
        run_id=run_id,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        requested_count=len(requests),
        fetched_count=len(result.histories),
        saved_count=writer.saved_count,
        fetch_failure_count=len(result.failures),
        write_failure_count=len(writer.failures),
        removed_old_file_count=removed_price_files,
        fetch_elapsed_seconds=result.elapsed_seconds,
        max_workers=MAX_WORKERS,
        max_queue_size=MAX_QUEUE_SIZE,
        max_attempts=MAX_ATTEMPTS,
        chart_created=chart_created,
        price_directory=str(OUTPUT_DIRECTORY),
        chart_path=str(COMPARISON_CHART),
        fetch_failures=tuple(
            FailureRecord(
                ticker=failure.ticker.symbol,
                message=failure.message,
            )
            for failure in result.failures
        ),
        write_failures=tuple(
            FailureRecord(
                ticker=failure.ticker.symbol,
                message=failure.message,
            )
            for failure in writer.failures
        ),
    )

    report_repository = JsonRunReportRepository(output_path=RUN_REPORT_PATH)
    report_repository.save(run_report)

    print("Результаты многопоточной загрузки и записи")
    print("=" * 50)
    print(f"Идентификатор запуска: {run_id}")
    print(f"Рабочих потоков загрузки: {MAX_WORKERS}")
    print(f"Максимальный размер очереди: {MAX_QUEUE_SIZE}")
    print(f"Максимальное число попыток: {MAX_ATTEMPTS}")
    print(f"Удалено старых файлов: {removed_price_files}")

    for history in result.histories:
        print(f"[ЗАГРУЖЕНО] {history.ticker.symbol}: {len(history.points)} точек")

    for failure in result.failures:
        print(f"[ОШИБКА ЗАГРУЗКИ] {failure.ticker.symbol}: {failure.message}")

    for failure in writer.failures:
        print(f"[ОШИБКА ЗАПИСИ] {failure.ticker.symbol}: {failure.message}")

    print("=" * 50)
    print(f"Запрошено историй: {len(requests)}")
    print(f"Загружено историй: {len(result.histories)}")
    print(f"Сохранено файлов: {writer.saved_count}")
    print(f"Ошибок загрузки: {len(result.failures)}")
    print(f"Ошибок записи: {len(writer.failures)}")
    print(f"Время загрузки: {result.elapsed_seconds:.3f} секунд")
    print(f"Каталог результатов: {OUTPUT_DIRECTORY}")
    print(f"Отчёт о запуске: {RUN_REPORT_PATH}")

    if chart_created:
        print(f"Сравнительный график: {COMPARISON_CHART}")
    else:
        print("Сравнительный график не построен: нет успешно сохранённых данных")


if __name__ == "__main__":
    main()
