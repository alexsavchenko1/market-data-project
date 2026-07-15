from dataclasses import dataclass
from queue import Queue
from threading import Thread

from market_data.models import PriceHistory, Ticker
from market_data.storage.base import PriceHistoryRepository


@dataclass(frozen=True, slots=True)
class WriteFailure:
    ticker: Ticker
    message: str


class BackgroundHistoryWriter:
    def __init__(
        self,
        repository: PriceHistoryRepository,
        max_queue_size: int,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError(
                "Размер очереди должен быть больше нуля"
            )

        self._repository = repository
        self._queue: Queue[PriceHistory | None] = Queue(
            maxsize=max_queue_size
        )

        self._thread = Thread(
            target=self._run,
            name="history-writer",
            daemon=False,
        )

        self._started = False
        self._closed = False
        self._saved_count = 0
        self._failures: list[WriteFailure] = []

    @property
    def saved_count(self) -> int:
        return self._saved_count

    @property
    def failures(self) -> tuple[WriteFailure, ...]:
        return tuple(self._failures)

    def start(self) -> None:
        if self._started:
            raise RuntimeError(
                "Поток записи уже был запущен"
            )

        self._started = True
        self._thread.start()

    def submit(self, history: PriceHistory) -> None:
        if not self._started:
            raise RuntimeError(
                "Поток записи ещё не запущен"
            )

        if self._closed:
            raise RuntimeError(
                "Поток записи уже завершён"
            )

        # Если очередь заполнена, вызывающий поток ждёт,
        # пока писатель освободит место. Это обратное давление.
        self._queue.put(history)

    def close(self) -> None:
        if not self._started:
            raise RuntimeError(
                "Поток записи ещё не запущен"
            )

        if self._closed:
            return

        # None используется как сигнал завершения.
        self._queue.put(None)
        self._queue.join()
        self._thread.join()

        self._closed = True

    def _run(self) -> None:
        while True:
            history = self._queue.get()

            try:
                if history is None:
                    return

                try:
                    self._repository.save(history)
                except Exception as error:
                    # Ошибка записи одного файла не должна
                    # останавливать обработку остальных результатов.
                    self._failures.append(
                        WriteFailure(
                            ticker=history.ticker,
                            message=str(error),
                        )
                    )
                else:
                    self._saved_count += 1
            finally:
                self._queue.task_done()