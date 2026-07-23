import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FailureRecord:
    ticker: str
    message: str


@dataclass(frozen=True, slots=True)
class RunReport:
    run_id: str
    started_at: str
    finished_at: str

    requested_count: int
    fetched_count: int
    saved_count: int

    fetch_failure_count: int
    write_failure_count: int
    retry_count: int
    removed_old_file_count: int

    fetch_elapsed_seconds: float

    max_workers: int
    max_queue_size: int
    max_attempts: int

    chart_created: bool
    price_directory: str
    chart_path: str
    event_log_path: str

    fetch_failures: tuple[FailureRecord, ...]
    write_failures: tuple[FailureRecord, ...]

    def to_dict(self) -> dict[str, object]:
        """Преобразует отчёт в структуру для сохранения в JSON."""

        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "requested_count": self.requested_count,
            "fetched_count": self.fetched_count,
            "saved_count": self.saved_count,
            "fetch_failure_count": self.fetch_failure_count,
            "write_failure_count": self.write_failure_count,
            "retry_count": self.retry_count,
            "removed_old_file_count": self.removed_old_file_count,
            "fetch_elapsed_seconds": self.fetch_elapsed_seconds,
            "max_workers": self.max_workers,
            "max_queue_size": self.max_queue_size,
            "max_attempts": self.max_attempts,
            "chart_created": self.chart_created,
            "price_directory": self.price_directory,
            "chart_path": self.chart_path,
            "event_log_path": self.event_log_path,
            "fetch_failures": [
                {
                    "ticker": failure.ticker,
                    "message": failure.message,
                }
                for failure in self.fetch_failures
            ],
            "write_failures": [
                {
                    "ticker": failure.ticker,
                    "message": failure.message,
                }
                for failure in self.write_failures
            ],
        }


class JsonRunReportRepository:
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def save(self, report: RunReport) -> None:
        """Атомарно сохраняет отчёт о запуске в JSON-файл."""

        self._output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self._output_path.with_suffix(f"{self._output_path.suffix}.tmp")

        serialized_report = json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            indent=2,
        )

        temporary_path.write_text(
            f"{serialized_report}\n",
            encoding="utf-8",
        )

        temporary_path.replace(self._output_path)
