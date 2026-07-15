import json
from pathlib import Path
from typing import cast

from market_data.observability.run_report import (
    FailureRecord,
    JsonRunReportRepository,
    RunReport,
)


def create_report() -> RunReport:
    return RunReport(
        run_id="test-run-id",
        started_at="2026-07-15T19:00:00+00:00",
        finished_at="2026-07-15T19:00:01+00:00",
        requested_count=3,
        fetched_count=2,
        saved_count=1,
        fetch_failure_count=1,
        write_failure_count=1,
        removed_old_file_count=4,
        fetch_elapsed_seconds=0.75,
        max_workers=5,
        max_queue_size=2,
        max_attempts=3,
        chart_created=True,
        price_directory="data/prices",
        chart_path="data/charts/comparison.png",
        fetch_failures=(
            FailureRecord(
                ticker="MSFT",
                message="Тестовая ошибка загрузки",
            ),
        ),
        write_failures=(
            FailureRecord(
                ticker="NVDA",
                message="Тестовая ошибка записи",
            ),
        ),
    )


def test_run_report_converts_to_dictionary() -> None:
    report = create_report()

    payload = report.to_dict()

    assert payload["run_id"] == "test-run-id"
    assert payload["requested_count"] == 3
    assert payload["fetched_count"] == 2
    assert payload["saved_count"] == 1
    assert payload["chart_created"] is True

    fetch_failures = cast(
        list[dict[str, object]],
        payload["fetch_failures"],
    )

    assert fetch_failures == [
        {
            "ticker": "MSFT",
            "message": "Тестовая ошибка загрузки",
        }
    ]


def test_json_repository_saves_run_report(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "reports" / "latest.json"

    repository = JsonRunReportRepository(output_path=output_path)

    repository.save(create_report())

    assert output_path.exists()
    assert not (tmp_path / "reports" / "latest.json.tmp").exists()

    payload = cast(
        dict[str, object],
        json.loads(output_path.read_text(encoding="utf-8")),
    )

    assert payload["run_id"] == "test-run-id"
    assert payload["fetch_elapsed_seconds"] == 0.75
    assert payload["price_directory"] == "data/prices"

    write_failures = cast(
        list[dict[str, object]],
        payload["write_failures"],
    )

    assert write_failures == [
        {
            "ticker": "NVDA",
            "message": "Тестовая ошибка записи",
        }
    ]


def test_json_repository_replaces_previous_report(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "latest.json"

    repository = JsonRunReportRepository(output_path=output_path)

    output_path.write_text(
        '{"old": true}',
        encoding="utf-8",
    )

    repository.save(create_report())

    payload = cast(
        dict[str, object],
        json.loads(output_path.read_text(encoding="utf-8")),
    )

    assert "old" not in payload
    assert payload["run_id"] == "test-run-id"
