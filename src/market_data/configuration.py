from collections.abc import Mapping
from dataclasses import dataclass
from os import environ
from pathlib import Path

DEFAULT_PROVIDER_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"

DEFAULT_REQUEST_FILE = "config/requests.csv"
DEFAULT_OUTPUT_DIRECTORY = "data/prices"
DEFAULT_COMPARISON_CHART = "data/charts/comparison.png"
DEFAULT_RUN_REPORT = "data/reports/latest.json"
DEFAULT_EVENT_LOG = "data/logs/latest.jsonl"

DEFAULT_MAX_WORKERS = 5
DEFAULT_MAX_QUEUE_SIZE = 2

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_INITIAL_RETRY_DELAY_SECONDS = 0.25
DEFAULT_RETRY_DELAY_MULTIPLIER = 2.0
DEFAULT_MAX_RETRY_DELAY_SECONDS = 2.0

DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    provider_base_url: str

    request_file: Path
    output_directory: Path
    comparison_chart_path: Path
    run_report_path: Path
    event_log_path: Path

    max_workers: int
    max_queue_size: int

    max_attempts: int
    initial_retry_delay_seconds: float
    retry_delay_multiplier: float
    max_retry_delay_seconds: float

    request_timeout_seconds: float
    connect_timeout_seconds: float

    def __post_init__(self) -> None:
        if not self.provider_base_url.startswith(("http://", "https://")):
            raise ValueError("Адрес поставщика должен начинаться с http:// или https://")

        if self.max_workers < 1:
            raise ValueError("Количество рабочих потоков должно быть больше нуля")

        if self.max_queue_size < 1:
            raise ValueError("Размер очереди должен быть больше нуля")

        if self.max_attempts < 1:
            raise ValueError("Количество попыток должно быть больше нуля")

        if self.initial_retry_delay_seconds < 0:
            raise ValueError("Начальная задержка не может быть отрицательной")

        if self.retry_delay_multiplier < 1:
            raise ValueError("Множитель задержки не может быть меньше единицы")

        if self.max_retry_delay_seconds < self.initial_retry_delay_seconds:
            raise ValueError("Максимальная задержка не может быть меньше начальной")

        if self.request_timeout_seconds <= 0:
            raise ValueError("Общий тайм-аут должен быть больше нуля")

        if self.connect_timeout_seconds <= 0:
            raise ValueError("Тайм-аут подключения должен быть больше нуля")


def load_settings(
    environment: Mapping[str, str] | None = None,
) -> ApplicationSettings:
    """Загружает настройки приложения из переменных окружения."""

    source = environ if environment is None else environment

    provider_base_url = _read_text(
        environment=source,
        key="MARKET_DATA_PROVIDER_URL",
        default=DEFAULT_PROVIDER_BASE_URL,
    )

    if not provider_base_url.endswith("/"):
        provider_base_url = f"{provider_base_url}/"

    return ApplicationSettings(
        provider_base_url=provider_base_url,
        request_file=Path(
            _read_text(
                environment=source,
                key="MARKET_DATA_REQUEST_FILE",
                default=DEFAULT_REQUEST_FILE,
            )
        ),
        output_directory=Path(
            _read_text(
                environment=source,
                key="MARKET_DATA_OUTPUT_DIRECTORY",
                default=DEFAULT_OUTPUT_DIRECTORY,
            )
        ),
        comparison_chart_path=Path(
            _read_text(
                environment=source,
                key="MARKET_DATA_COMPARISON_CHART",
                default=DEFAULT_COMPARISON_CHART,
            )
        ),
        run_report_path=Path(
            _read_text(
                environment=source,
                key="MARKET_DATA_RUN_REPORT",
                default=DEFAULT_RUN_REPORT,
            )
        ),
        event_log_path=Path(
            _read_text(
                environment=source,
                key="MARKET_DATA_EVENT_LOG",
                default=DEFAULT_EVENT_LOG,
            )
        ),
        max_workers=_read_int(
            environment=source,
            key="MARKET_DATA_MAX_WORKERS",
            default=DEFAULT_MAX_WORKERS,
        ),
        max_queue_size=_read_int(
            environment=source,
            key="MARKET_DATA_MAX_QUEUE_SIZE",
            default=DEFAULT_MAX_QUEUE_SIZE,
        ),
        max_attempts=_read_int(
            environment=source,
            key="MARKET_DATA_MAX_ATTEMPTS",
            default=DEFAULT_MAX_ATTEMPTS,
        ),
        initial_retry_delay_seconds=_read_float(
            environment=source,
            key="MARKET_DATA_INITIAL_RETRY_DELAY_SECONDS",
            default=DEFAULT_INITIAL_RETRY_DELAY_SECONDS,
        ),
        retry_delay_multiplier=_read_float(
            environment=source,
            key="MARKET_DATA_RETRY_DELAY_MULTIPLIER",
            default=DEFAULT_RETRY_DELAY_MULTIPLIER,
        ),
        max_retry_delay_seconds=_read_float(
            environment=source,
            key="MARKET_DATA_MAX_RETRY_DELAY_SECONDS",
            default=DEFAULT_MAX_RETRY_DELAY_SECONDS,
        ),
        request_timeout_seconds=_read_float(
            environment=source,
            key="MARKET_DATA_REQUEST_TIMEOUT_SECONDS",
            default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
        connect_timeout_seconds=_read_float(
            environment=source,
            key="MARKET_DATA_CONNECT_TIMEOUT_SECONDS",
            default=DEFAULT_CONNECT_TIMEOUT_SECONDS,
        ),
    )


def _read_text(
    environment: Mapping[str, str],
    key: str,
    default: str,
) -> str:
    value = environment.get(
        key,
        default,
    ).strip()

    if not value:
        raise ValueError(f"Переменная {key} не может быть пустой")

    return value


def _read_int(
    environment: Mapping[str, str],
    key: str,
    default: int,
) -> int:
    raw_value = environment.get(
        key,
        str(default),
    ).strip()

    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"Переменная {key} должна содержать целое число") from error


def _read_float(
    environment: Mapping[str, str],
    key: str,
    default: float,
) -> float:
    raw_value = environment.get(
        key,
        str(default),
    ).strip()

    try:
        return float(raw_value)
    except ValueError as error:
        raise ValueError(f"Переменная {key} должна содержать число") from error
