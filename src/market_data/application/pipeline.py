from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from market_data.analysis.comparison import PriceComparisonBuilder
from market_data.application.background_writer import (
    BackgroundHistoryWriter,
    WriteFailure,
)
from market_data.application.batch_result import BatchFetchResult
from market_data.application.concurrent import (
    fetch_histories_concurrently,
)
from market_data.models import PriceHistoryRequest
from market_data.observability.run_report import (
    FailureRecord,
    JsonRunReportRepository,
    RunReport,
)
from market_data.providers.base import MarketDataProvider
from market_data.storage.csv_repository import (
    CsvPriceHistoryRepository,
)


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    output_directory: Path
    comparison_chart_path: Path

    max_workers: int
    max_queue_size: int
    max_attempts: int


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    batch_result: BatchFetchResult
    write_failures: tuple[WriteFailure, ...]

    saved_count: int
    removed_old_file_count: int
    chart_created: bool

    report: RunReport


class MarketDataPipeline:
    def __init__(
        self,
        provider: MarketDataProvider,
        price_repository: CsvPriceHistoryRepository,
        comparison_builder: PriceComparisonBuilder,
        report_repository: JsonRunReportRepository,
        config: PipelineConfig,
        run_id_factory: Callable[[], str] | None = None,
        now_function: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._price_repository = price_repository
        self._comparison_builder = comparison_builder
        self._report_repository = report_repository
        self._config = config

        self._run_id_factory = (
            run_id_factory if run_id_factory is not None else lambda: str(uuid4())
        )

        self._now = now_function if now_function is not None else lambda: datetime.now(UTC)

    def run(
        self,
        requests: tuple[PriceHistoryRequest, ...],
    ) -> PipelineRunResult:
        """Выполняет полный конвейер обработки рыночных данных."""

        if not requests:
            raise ValueError("Для запуска конвейера необходим хотя бы один запрос")

        run_id = self._run_id_factory()
        started_at = self._now()

        removed_old_file_count = self._price_repository.clear()

        # Старый график не должен выглядеть как результат
        # нового неуспешного запуска.
        self._config.comparison_chart_path.unlink(missing_ok=True)

        writer = BackgroundHistoryWriter(
            repository=self._price_repository,
            max_queue_size=self._config.max_queue_size,
        )

        writer.start()

        try:
            batch_result = fetch_histories_concurrently(
                requests=requests,
                provider=self._provider,
                max_workers=self._config.max_workers,
                on_history_fetched=writer.submit,
            )
        finally:
            writer.close()

        chart_created = self._create_chart_if_possible(saved_count=writer.saved_count)

        finished_at = self._now()

        report = self._build_report(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            requests=requests,
            batch_result=batch_result,
            write_failures=writer.failures,
            saved_count=writer.saved_count,
            removed_old_file_count=(removed_old_file_count),
            chart_created=chart_created,
        )

        self._report_repository.save(report)

        return PipelineRunResult(
            batch_result=batch_result,
            write_failures=writer.failures,
            saved_count=writer.saved_count,
            removed_old_file_count=(removed_old_file_count),
            chart_created=chart_created,
            report=report,
        )

    def _create_chart_if_possible(
        self,
        saved_count: int,
    ) -> bool:
        if saved_count == 0:
            return False

        normalized_series = self._comparison_builder.load_and_normalize(
            self._config.output_directory
        )

        self._comparison_builder.save_chart(
            series=normalized_series,
            output_path=(self._config.comparison_chart_path),
        )

        return True

    def _build_report(
        self,
        run_id: str,
        started_at: datetime,
        finished_at: datetime,
        requests: tuple[PriceHistoryRequest, ...],
        batch_result: BatchFetchResult,
        write_failures: tuple[WriteFailure, ...],
        saved_count: int,
        removed_old_file_count: int,
        chart_created: bool,
    ) -> RunReport:
        return RunReport(
            run_id=run_id,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            requested_count=len(requests),
            fetched_count=len(batch_result.histories),
            saved_count=saved_count,
            fetch_failure_count=len(batch_result.failures),
            write_failure_count=len(write_failures),
            removed_old_file_count=(removed_old_file_count),
            fetch_elapsed_seconds=(batch_result.elapsed_seconds),
            max_workers=self._config.max_workers,
            max_queue_size=(self._config.max_queue_size),
            max_attempts=self._config.max_attempts,
            chart_created=chart_created,
            price_directory=str(self._config.output_directory),
            chart_path=str(self._config.comparison_chart_path),
            fetch_failures=tuple(
                FailureRecord(
                    ticker=failure.ticker.symbol,
                    message=failure.message,
                )
                for failure in batch_result.failures
            ),
            write_failures=tuple(
                FailureRecord(
                    ticker=failure.ticker.symbol,
                    message=failure.message,
                )
                for failure in write_failures
            ),
        )
