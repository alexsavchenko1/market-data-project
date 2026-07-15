class MarketDataError(Exception):
    """Базовая ошибка сервиса рыночных данных."""


class MarketDataRequestError(MarketDataError):
    """Ошибка выполнения запроса к поставщику данных."""


class MarketDataTransientError(MarketDataRequestError):
    """Временная ошибка, после которой запрос можно повторить."""


class MarketDataResponseError(MarketDataError):
    """Ошибка структуры или содержимого ответа поставщика."""
