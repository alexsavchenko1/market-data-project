import json
from pathlib import Path
from typing import cast

from market_data.models import Ticker
from market_data.observability.event_log import (
    JsonLineEventLogger,
)
from market_data.observability.retry_metrics import (
    RetryEventObserver,
    RetryMetrics,
)
from market_data.providers.retrying import RetryEvent


def create_retry_event() -> RetryEvent:
    return RetryEvent(
        ticker=Ticker("AAPL"),
        failed_attempt_number=1,
        next_attempt_number=2,
        delay_seconds=0.25,
        message="Временная ошибка",
        occurred_at=("2026-07-23T12:00:00+00:00"),
    )


def test_retry_metrics_collects_events() -> None:
    metrics = RetryMetrics()
    event = create_retry_event()

    metrics.record(event)

    assert metrics.count == 1
    assert metrics.events == (event,)

    metrics.reset()

    assert metrics.count == 0
    assert metrics.events == ()


def test_retry_observer_records_metric_and_log(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "latest.jsonl"

    logger = JsonLineEventLogger(output_path=log_path)
    logger.start_run("test-run")

    metrics = RetryMetrics()

    observer = RetryEventObserver(
        metrics=metrics,
        event_logger=logger,
    )

    observer(create_retry_event())

    assert metrics.count == 1

    line = log_path.read_text(encoding="utf-8").strip()

    payload = cast(
        dict[str, object],
        json.loads(line),
    )

    assert payload["event"] == "retry_scheduled"
    assert payload["run_id"] == "test-run"
    assert payload["timestamp"] == ("2026-07-23T12:00:00+00:00")

    details = cast(
        dict[str, object],
        payload["details"],
    )

    assert details["ticker"] == "AAPL"
    assert details["next_attempt_number"] == 2
