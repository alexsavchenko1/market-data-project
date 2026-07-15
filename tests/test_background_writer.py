from datetime import date
from decimal import Decimal
from threading import current_thread

import pytest

from market_data.application.background_writer import (
    BackgroundHistoryWriter,
)
from market_data.models import (
    PriceHistory,
    PricePoint,
    Ticker,
)


class RecordingRepository:
    def __init__(self) -> None:
        self.saved_tickers: list[str] = []
        self.thread_names: list[str] = []

    def save(self, history: PriceHistory) -> None:
        self.saved_tickers.append(
            history.ticker.symbol
        )
        self.thread_names.append(
            current_thread().name
        )


class PartiallyFailingRepository:
    def __init__(self) -> None:
        self.saved_tickers: list[str] = []

    def save(self, history: PriceHistory) -> None:
        if history.ticker == Ticker("MSFT"):
            raise OSError("Тестовая ошибка записи")

        self.saved_tickers.append(
            history.ticker.symbol
        )


def create_history(symbol: str) -> PriceHistory:
    return PriceHistory(
        ticker=Ticker(symbol),
        currency="USD",
        points=(
            PricePoint(
                trading_date=date(2025, 1, 2),
                adjusted_close=Decimal("100"),
            ),
        ),
    )


def test_background_writer_uses_separate_thread() -> None:
    repository = RecordingRepository()
    writer = BackgroundHistoryWriter(
        repository=repository,
        max_queue_size=2,
    )

    writer.start()
    writer.submit(create_history("AAPL"))
    writer.submit(create_history("MSFT"))
    writer.close()

    assert repository.saved_tickers == [
        "AAPL",
        "MSFT",
    ]
    assert repository.thread_names == [
        "history-writer",
        "history-writer",
    ]
    assert writer.saved_count == 2
    assert writer.failures == ()


def test_background_writer_continues_after_failure() -> None:
    repository = PartiallyFailingRepository()
    writer = BackgroundHistoryWriter(
        repository=repository,
        max_queue_size=2,
    )

    writer.start()
    writer.submit(create_history("AAPL"))
    writer.submit(create_history("MSFT"))
    writer.submit(create_history("NVDA"))
    writer.close()

    assert repository.saved_tickers == [
        "AAPL",
        "NVDA",
    ]
    assert writer.saved_count == 2
    assert len(writer.failures) == 1
    assert writer.failures[0].ticker == Ticker("MSFT")


def test_background_writer_rejects_invalid_queue_size() -> None:
    repository = RecordingRepository()

    with pytest.raises(
        ValueError,
        match="Размер очереди должен быть больше нуля",
    ):
        BackgroundHistoryWriter(
            repository=repository,
            max_queue_size=0,
        )