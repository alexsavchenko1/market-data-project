from pathlib import Path

import httpx

from market_data.analysis.comparison import (
    PriceComparisonBuilder,
)
from market_data.application.pipeline import (
    MarketDataPipeline,
    PipelineConfig,
    PipelineRunResult,
)
from market_data.observability.event_log import (
    JsonLineEventLogger,
)
from market_data.observability.retry_metrics import (
    RetryEventObserver,
    RetryMetrics,
)
from market_data.observability.run_report import (
    JsonRunReportRepository,
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
EVENT_LOG_PATH = Path("data/logs/latest.jsonl")

MAX_WORKERS = 5
MAX_QUEUE_SIZE = 2

MAX_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 0.25
RETRY_DELAY_MULTIPLIER = 2.0
MAX_RETRY_DELAY_SECONDS = 2.0


def print_result(
    result: PipelineRunResult,
) -> None:
    """Выводит итог выполнения конвейера в терминал."""

    print("Результаты многопоточной загрузки и записи")
    print("=" * 50)
    print(f"Идентификатор запуска: {result.report.run_id}")
    print(f"Рабочих потоков загрузки: {result.report.max_workers}")
    print(f"Максимальный размер очереди: {result.report.max_queue_size}")
    print(f"Максимальное число попыток: {result.report.max_attempts}")
    print(f"Удалено старых файлов: {result.removed_old_file_count}")

    for history in result.batch_result.histories:
        print(f"[ЗАГРУЖЕНО] {history.ticker.symbol}: {len(history.points)} точек")

    for failure in result.batch_result.failures:
        print(f"[ОШИБКА ЗАГРУЗКИ] {failure.ticker.symbol}: {failure.message}")

    for failure in result.write_failures:
        print(f"[ОШИБКА ЗАПИСИ] {failure.ticker.symbol}: {failure.message}")

    print("=" * 50)
    print(f"Запрошено историй: {result.report.requested_count}")
    print(f"Загружено историй: {result.report.fetched_count}")
    print(f"Сохранено файлов: {result.saved_count}")
    print(f"Повторных попыток: {result.retry_count}")
    print(f"Ошибок загрузки: {result.report.fetch_failure_count}")
    print(f"Ошибок записи: {result.report.write_failure_count}")
    print(f"Время загрузки: {result.report.fetch_elapsed_seconds:.3f} секунд")
    print(f"Каталог результатов: {result.report.price_directory}")
    print(f"Отчёт о запуске: {RUN_REPORT_PATH}")
    print(f"Журнал событий: {result.report.event_log_path}")

    if result.chart_created:
        print(f"Сравнительный график: {result.report.chart_path}")
    else:
        print("Сравнительный график не построен: нет успешно сохранённых данных")


def main() -> None:
    requests = tuple(generate_price_history_requests(REQUEST_FILE))

    if not requests:
        raise SystemExit("Файл не содержит запросов")

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    config = PipelineConfig(
        output_directory=OUTPUT_DIRECTORY,
        comparison_chart_path=COMPARISON_CHART,
        event_log_path=EVENT_LOG_PATH,
        max_workers=MAX_WORKERS,
        max_queue_size=MAX_QUEUE_SIZE,
        max_attempts=MAX_ATTEMPTS,
    )

    price_repository = CsvPriceHistoryRepository(output_directory=OUTPUT_DIRECTORY)
    comparison_builder = PriceComparisonBuilder()
    report_repository = JsonRunReportRepository(output_path=RUN_REPORT_PATH)

    event_logger = JsonLineEventLogger(output_path=EVENT_LOG_PATH)
    retry_metrics = RetryMetrics()
    retry_observer = RetryEventObserver(
        metrics=retry_metrics,
        event_logger=event_logger,
    )

    retry_policy = RetryPolicy(
        max_attempts=MAX_ATTEMPTS,
        initial_delay_seconds=(INITIAL_RETRY_DELAY_SECONDS),
        multiplier=RETRY_DELAY_MULTIPLIER,
        max_delay_seconds=(MAX_RETRY_DELAY_SECONDS),
    )

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
            on_retry=retry_observer,
        )

        pipeline = MarketDataPipeline(
            provider=provider,
            price_repository=price_repository,
            comparison_builder=comparison_builder,
            report_repository=report_repository,
            event_logger=event_logger,
            retry_metrics=retry_metrics,
            config=config,
        )

        result = pipeline.run(requests)

    print_result(result)


if __name__ == "__main__":
    main()
