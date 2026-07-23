import json
from pathlib import Path
from typing import cast

import pytest

from market_data.observability.event_log import (
    JsonLineEventLogger,
)


def test_event_logger_writes_json_lines(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "latest.jsonl"

    logger = JsonLineEventLogger(output_path=output_path)
    logger.start_run("test-run")

    logger.emit(
        event_name="run_started",
        occurred_at=("2026-07-23T12:00:00+00:00"),
        details={
            "max_workers": 5,
        },
    )

    logger.emit(
        event_name="run_finished",
        occurred_at=("2026-07-23T12:00:01+00:00"),
        details={
            "success": True,
        },
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2

    first_event = cast(
        dict[str, object],
        json.loads(lines[0]),
    )
    second_event = cast(
        dict[str, object],
        json.loads(lines[1]),
    )

    assert first_event["run_id"] == "test-run"
    assert first_event["event"] == "run_started"
    assert second_event["event"] == "run_finished"

    first_details = cast(
        dict[str, object],
        first_event["details"],
    )

    assert first_details["max_workers"] == 5


def test_event_logger_replaces_previous_run(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "latest.jsonl"

    logger = JsonLineEventLogger(output_path=output_path)

    logger.start_run("first-run")
    logger.emit("first-event")

    logger.start_run("second-run")
    logger.emit("second-event")

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    event = cast(
        dict[str, object],
        json.loads(lines[0]),
    )

    assert event["run_id"] == "second-run"
    assert event["event"] == "second-event"


def test_event_logger_requires_started_run(
    tmp_path: Path,
) -> None:
    logger = JsonLineEventLogger(output_path=(tmp_path / "latest.jsonl"))

    with pytest.raises(
        RuntimeError,
        match="Журнал запуска ещё не инициализирован",
    ):
        logger.emit("run_started")
