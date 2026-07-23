from pathlib import Path

import pytest

from market_data.configuration import load_settings


def test_load_settings_uses_default_values() -> None:
    settings = load_settings({})

    assert settings.provider_base_url == ("https://query1.finance.yahoo.com/v8/finance/chart/")
    assert settings.request_file == Path("config/requests.csv")
    assert settings.output_directory == Path("data/prices")
    assert settings.max_workers == 5
    assert settings.max_queue_size == 2
    assert settings.max_attempts == 3
    assert settings.request_timeout_seconds == 10.0


def test_load_settings_applies_environment_overrides() -> None:
    settings = load_settings(
        {
            "MARKET_DATA_PROVIDER_URL": ("http://localhost:8080/api"),
            "MARKET_DATA_REQUEST_FILE": ("config/load-test.csv"),
            "MARKET_DATA_OUTPUT_DIRECTORY": ("tmp/prices"),
            "MARKET_DATA_MAX_WORKERS": "12",
            "MARKET_DATA_MAX_QUEUE_SIZE": "4",
            "MARKET_DATA_MAX_ATTEMPTS": "5",
            "MARKET_DATA_INITIAL_RETRY_DELAY_SECONDS": ("0.1"),
            "MARKET_DATA_RETRY_DELAY_MULTIPLIER": ("3"),
            "MARKET_DATA_MAX_RETRY_DELAY_SECONDS": ("5"),
            "MARKET_DATA_REQUEST_TIMEOUT_SECONDS": ("20"),
            "MARKET_DATA_CONNECT_TIMEOUT_SECONDS": ("2"),
        }
    )

    assert settings.provider_base_url == ("http://localhost:8080/api/")
    assert settings.request_file == Path("config/load-test.csv")
    assert settings.output_directory == Path("tmp/prices")
    assert settings.max_workers == 12
    assert settings.max_queue_size == 4
    assert settings.max_attempts == 5
    assert settings.initial_retry_delay_seconds == 0.1
    assert settings.retry_delay_multiplier == 3
    assert settings.max_retry_delay_seconds == 5
    assert settings.request_timeout_seconds == 20
    assert settings.connect_timeout_seconds == 2


def test_load_settings_rejects_invalid_integer() -> None:
    with pytest.raises(
        ValueError,
        match=("MARKET_DATA_MAX_WORKERS должна содержать целое число"),
    ):
        load_settings(
            {
                "MARKET_DATA_MAX_WORKERS": ("много"),
            }
        )


def test_load_settings_rejects_invalid_provider_url() -> None:
    with pytest.raises(
        ValueError,
        match=("Адрес поставщика должен начинаться"),
    ):
        load_settings(
            {
                "MARKET_DATA_PROVIDER_URL": ("localhost:8080"),
            }
        )


def test_load_settings_rejects_invalid_retry_delays() -> None:
    with pytest.raises(
        ValueError,
        match=("Максимальная задержка не может быть меньше начальной"),
    ):
        load_settings(
            {
                "MARKET_DATA_INITIAL_RETRY_DELAY_SECONDS": ("3"),
                "MARKET_DATA_MAX_RETRY_DELAY_SECONDS": ("1"),
            }
        )
