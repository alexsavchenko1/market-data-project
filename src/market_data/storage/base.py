from typing import Protocol

from market_data.models import PriceHistory


class PriceHistoryRepository(Protocol):
    def save(self, history: PriceHistory) -> None:
        """Сохраняет историю цен."""
        ...