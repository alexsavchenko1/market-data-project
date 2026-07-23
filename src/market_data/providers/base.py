from typing import Protocol

from market_data.models import PriceHistory, PriceHistoryRequest


class MarketDataProvider(Protocol):
    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        """Получает историю цен по заданным параметрам."""
        ...
