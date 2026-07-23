import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from market_data.analysis.comparison import (
    PriceComparisonBuilder,
)
from market_data.application.pipeline import (
    MarketDataPipeline,
    PipelineConfig,
)
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)
from market_data.observability.event_log import (
    JsonLineEventLogger,
)
from market_data.observability.retry_metrics import (
    RetryMetrics,
)
from market_data.observability.run_report import (
    JsonRunReportRepository,
)
from market_data.storage.csv_repository import (
    CsvPriceHistoryRepository,
)


class StubMarketDataProvider:
    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        return PriceHistory(
            ticker=request.ticker,
            currency="USD",
            points=(
                PricePoint(
                    trading_date=date(2025, 1, 2),
                    adjusted_close=Decimal("100"),
                ),
                PricePoint(
                    trading_date=date(2025, 1, 3),
                    adjusted_close=Decimal("110"),
                ),
            ),
        )


def create_request(
    symbol: str,
) -> PriceHistoryRequest:
    return PriceHistoryRequest(
        ticker=Ticker(symbol),
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 10),
    )


def test_pipeline_creates_files_chart_report_and_log(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "prices"
    chart_path = tmp_path / "charts" / "comparison.png"
    report_path = tmp_path / "reports" / "latest.json"
    event_log_path = tmp_path / "logs" / "latest.jsonl"

    moments = iter(
        (
            datetime(
                2026,
                7,
                23,
                10,
                0,
                tzinfo=UTC,
            ),
            datetime(
                2026,
                7,
                23,
                10,
                1,
                tzinfo=UTC,
            ),
        )
    )

    def fixed_now() -> datetime:
        return next(moments)

    pipeline = MarketDataPipeline(
        provider=StubMarketDataProvider(),
        price_repository=CsvPriceHistoryRepository(output_directory),
        comparison_builder=PriceComparisonBuilder(),
        report_repository=JsonRunReportRepository(report_path),
        event_logger=JsonLineEventLogger(output_path=event_log_path),
        retry_metrics=RetryMetrics(),
        config=PipelineConfig(
            output_directory=output_directory,
            comparison_chart_path=chart_path,
            event_log_path=event_log_path,
            max_workers=2,
            max_queue_size=1,
            max_attempts=3,
        ),
        run_id_factory=lambda: "test-run-id",
        now_function=fixed_now,
    )

    result = pipeline.run(
        (
            create_request("AAPL"),
            create_request("MSFT"),
        )
    )

    assert result.saved_count == 2
    assert result.retry_count == 0
    assert result.chart_created is True
    assert result.write_failures == ()

    assert (output_directory / "AAPL.csv").exists()
    assert (output_directory / "MSFT.csv").exists()
    assert chart_path.exists()
    assert report_path.exists()
    assert event_log_path.exists()

    payload = cast(
        dict[str, object],
        json.loads(report_path.read_text(encoding="utf-8")),
    )

    assert payload["run_id"] == "test-run-id"
    assert payload["requested_count"] == 2
    assert payload["fetched_count"] == 2
    assert payload["saved_count"] == 2
    assert payload["retry_count"] == 0
    assert payload["chart_created"] is True
    assert payload["max_workers"] == 2
    assert payload["event_log_path"] == str(event_log_path)

    events = [
        cast(
            dict[str, object],
            json.loads(line),
        )
        for line in event_log_path.read_text(encoding="utf-8").splitlines()
    ]

    event_names = [cast(str, event["event"]) for event in events]

    assert event_names == [
        "run_started",
        "history_fetched",
        "history_fetched",
        "chart_created",
        "run_finished",
    ]


def test_pipeline_removes_stale_price_files(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "prices"
    output_directory.mkdir()

    stale_file = output_directory / "STALE.csv"
    stale_file.write_text(
        "old",
        encoding="utf-8",
    )

    event_log_path = tmp_path / "latest.jsonl"

    pipeline = MarketDataPipeline(
        provider=StubMarketDataProvider(),
        price_repository=CsvPriceHistoryRepository(output_directory),
        comparison_builder=PriceComparisonBuilder(),
        report_repository=JsonRunReportRepository(tmp_path / "latest.json"),
        event_logger=JsonLineEventLogger(output_path=event_log_path),
        retry_metrics=RetryMetrics(),
        config=PipelineConfig(
            output_directory=output_directory,
            comparison_chart_path=(tmp_path / "comparison.png"),
            event_log_path=event_log_path,
            max_workers=1,
            max_queue_size=1,
            max_attempts=3,
        ),
        run_id_factory=lambda: "test-run-id",
    )

    result = pipeline.run((create_request("AAPL"),))

    assert not stale_file.exists()
    assert result.removed_old_file_count == 1
    assert (output_directory / "AAPL.csv").exists()
