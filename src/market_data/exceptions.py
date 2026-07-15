class MarketDataError(Exception):
    """Базовая ошибка получения рыночных данных."""


class MarketDataRequestError(MarketDataError):
    """Ошибка выполнения запроса к внешнему источнику."""


class MarketDataResponseError(MarketDataError):
    """Ошибка структуры или содержимого ответа."""
