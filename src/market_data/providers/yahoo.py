from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import cast

import httpx

from market_data.exceptions import (
    MarketDataRequestError,
    MarketDataResponseError,
)
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
    Ticker,
)


def _as_mapping(
    value: object,
    field_name: str,
) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise MarketDataResponseError(
            f"Поле '{field_name}' должно быть объектом"
        )

    return cast(dict[str, object], value)


def _as_list(
    value: object,
    field_name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise MarketDataResponseError(
            f"Поле '{field_name}' должно быть списком"
        )

    return cast(list[object], value)


def _to_unix_timestamp(value: date) -> int:
    moment = datetime.combine(
        value,
        time.min,
        tzinfo=UTC,
    )
    return int(moment.timestamp())


def parse_yahoo_history(
    payload: object,
    ticker: Ticker,
) -> PriceHistory:
    """Преобразует ответ Yahoo Finance в предметную модель."""

    root = _as_mapping(payload, "root")
    chart = _as_mapping(root.get("chart"), "chart")

    chart_error = chart.get("error")

    if chart_error is not None:
        raise MarketDataResponseError(
            f"Yahoo Finance вернул ошибку: {chart_error}"
        )

    results = _as_list(chart.get("result"), "chart.result")

    if not results:
        raise MarketDataResponseError(
            "Yahoo Finance не вернул данные по тикеру"
        )

    result = _as_mapping(results[0], "chart.result[0]")
    meta = _as_mapping(result.get("meta"), "meta")

    currency = meta.get("currency")

    if not isinstance(currency, str) or not currency.strip():
        raise MarketDataResponseError(
            "В ответе отсутствует валюта инструмента"
        )

    timestamps = _as_list(
        result.get("timestamp"),
        "timestamp",
    )

    indicators = _as_mapping(
        result.get("indicators"),
        "indicators",
    )

    adjusted_close_blocks = _as_list(
        indicators.get("adjclose"),
        "indicators.adjclose",
    )

    if not adjusted_close_blocks:
        raise MarketDataResponseError(
            "В ответе отсутствуют скорректированные цены"
        )

    adjusted_close_block = _as_mapping(
        adjusted_close_blocks[0],
        "indicators.adjclose[0]",
    )

    prices = _as_list(
        adjusted_close_block.get("adjclose"),
        "indicators.adjclose[0].adjclose",
    )

    if len(timestamps) != len(prices):
        raise MarketDataResponseError(
            "Количество дат не совпадает с количеством цен"
        )

    points: list[PricePoint] = []

    for timestamp_value, price_value in zip(timestamps, prices, strict=True):
        # Yahoo может вернуть null для дня без доступной цены.
        if price_value is None:
            continue

        if (
            isinstance(timestamp_value, bool)
            or not isinstance(timestamp_value, (int, float))
        ):
            raise MarketDataResponseError(
                "Ответ содержит некорректную временную метку"
            )

        if (
            isinstance(price_value, bool)
            or not isinstance(price_value, (int, float, str))
        ):
            raise MarketDataResponseError(
                "Ответ содержит некорректную цену"
            )

        try:
            adjusted_close = Decimal(str(price_value))
            trading_date = datetime.fromtimestamp(
                timestamp_value,
                tz=UTC,
            ).date()

            point = PricePoint(
                trading_date=trading_date,
                adjusted_close=adjusted_close,
            )
        except (InvalidOperation, OSError, OverflowError, ValueError) as error:
            raise MarketDataResponseError(
                "Не удалось преобразовать точку истории цен"
            ) from error

        points.append(point)

    try:
        return PriceHistory(
            ticker=ticker,
            currency=currency,
            points=tuple(points),
        )
    except ValueError as error:
        raise MarketDataResponseError(
            "Yahoo Finance вернул некорректную историю цен"
        ) from error


class YahooFinanceProvider:
    def __init__(
        self,
        client: httpx.Client,
    ) -> None:
        self._client = client

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        params = {
            "period1": str(_to_unix_timestamp(request.date_from)),
            "period2": str(_to_unix_timestamp(request.date_to)),
            "interval": request.interval.value,
            "events": "history",
            "includeAdjustedClose": "true",
        }

        try:
            response = self._client.get(
                f"/{request.ticker.symbol}",
                params=params,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise MarketDataRequestError(
                f"Не удалось получить данные для "
                f"{request.ticker.symbol}"
            ) from error

        try:
            payload = cast(object, response.json())
        except ValueError as error:
            raise MarketDataResponseError(
                "Yahoo Finance вернул некорректный JSON"
            ) from error

        return parse_yahoo_history(
            payload=payload,
            ticker=request.ticker,
        )