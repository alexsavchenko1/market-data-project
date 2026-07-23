import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

JsonScalar = str | int | float | bool | None


class JsonLineEventLogger:
    def __init__(
        self,
        output_path: Path,
    ) -> None:
        self._output_path = output_path
        self._run_id: str | None = None
        self._lock = Lock()

    def start_run(
        self,
        run_id: str,
    ) -> None:
        """Начинает новый журнал и удаляет данные прошлого запуска."""

        if not run_id.strip():
            raise ValueError("Идентификатор запуска не может быть пустым")

        with self._lock:
            self._output_path.unlink(missing_ok=True)
            self._run_id = run_id

    def emit(
        self,
        event_name: str,
        details: Mapping[str, JsonScalar] | None = None,
        occurred_at: str | None = None,
    ) -> None:
        """Добавляет одно структурированное событие в журнал."""

        if not event_name.strip():
            raise ValueError("Название события не может быть пустым")

        normalized_details: dict[
            str,
            JsonScalar,
        ] = {} if details is None else dict(details)

        with self._lock:
            if self._run_id is None:
                raise RuntimeError("Журнал запуска ещё не инициализирован")

            payload: dict[str, object] = {
                "timestamp": (
                    occurred_at if occurred_at is not None else datetime.now(UTC).isoformat()
                ),
                "run_id": self._run_id,
                "event": event_name,
                "details": normalized_details,
            }

            serialized_event = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            self._output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with self._output_path.open(
                mode="a",
                encoding="utf-8",
            ) as file:
                file.write(serialized_event)
                file.write("\n")
