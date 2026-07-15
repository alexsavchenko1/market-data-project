from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import cast

import httpx

from market_data.exceptions import (
    MarketDataRequestError,
    MarketDataResponseError,
    MarketDataTransientError,
)
from market_data.models import (
    PriceHistory,
    PriceHistoryRequest,
    PricePoint,
)


class YahooFinanceProvider:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_history(
        self,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        """Получает историю цен через Yahoo Finance."""

        parameters: dict[str, str | int] = {
            "period1": self._to_unix_timestamp(request.date_from),
            "period2": self._to_unix_timestamp(request.date_to),
            "interval": request.interval.value,
            "events": "history",
            "includeAdjustedClose": "true",
        }

        try:
            response = self._client.get(
                request.ticker.symbol,
                params=parameters,
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code

            if status_code in {408, 429} or 500 <= status_code < 600:
                raise MarketDataTransientError(
                    f"Yahoo Finance временно недоступен для "
                    f"{request.ticker.symbol}: HTTP {status_code}"
                ) from error

            raise MarketDataRequestError(
                f"Yahoo Finance отклонил запрос для {request.ticker.symbol}: HTTP {status_code}"
            ) from error

        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        ) as error:
            raise MarketDataTransientError(
                f"Временная сетевая ошибка при загрузке {request.ticker.symbol}: {error}"
            ) from error

        except httpx.RequestError as error:
            raise MarketDataRequestError(
                f"Не удалось выполнить запрос для {request.ticker.symbol}: {error}"
            ) from error

        try:
            payload = cast(object, response.json())
        except ValueError as error:
            raise MarketDataResponseError(
                f"Yahoo Finance вернул некорректный JSON для {request.ticker.symbol}"
            ) from error

        return self._parse_payload(
            payload=payload,
            request=request,
        )

    def _parse_payload(
        self,
        payload: object,
        request: PriceHistoryRequest,
    ) -> PriceHistory:
        root = self._require_mapping(
            payload,
            "корневой объект",
        )

        chart = self._require_mapping(
            root.get("chart"),
            "chart",
        )

        provider_error = chart.get("error")

        if provider_error is not None:
            raise MarketDataResponseError(
                f"Yahoo Finance вернул ошибку для {request.ticker.symbol}: {provider_error}"
            )

        results = self._require_list(
            chart.get("result"),
            "chart.result",
        )

        if not results:
            raise MarketDataResponseError(
                f"Yahoo Finance не вернул данные для {request.ticker.symbol}"
            )

        result = self._require_mapping(
            results[0],
            "chart.result[0]",
        )

        metadata = self._require_mapping(
            result.get("meta"),
            "meta",
        )

        currency_raw = metadata.get("currency")

        if not isinstance(currency_raw, str) or not currency_raw.strip():
            raise MarketDataResponseError(
                f"В ответе для {request.ticker.symbol} отсутствует валюта"
            )

        timestamps = self._require_list(
            result.get("timestamp"),
            "timestamp",
        )

        indicators = self._require_mapping(
            result.get("indicators"),
            "indicators",
        )

        adjusted_close_items = self._require_list(
            indicators.get("adjclose"),
            "indicators.adjclose",
        )

        if not adjusted_close_items:
            raise MarketDataResponseError(
                f"В ответе для {request.ticker.symbol} отсутствуют скорректированные цены"
            )

        adjusted_close_container = self._require_mapping(
            adjusted_close_items[0],
            "indicators.adjclose[0]",
        )

        prices = self._require_list(
            adjusted_close_container.get("adjclose"),
            "indicators.adjclose[0].adjclose",
        )

        if len(timestamps) != len(prices):
            raise MarketDataResponseError(
                f"Количество дат и цен не совпадает для {request.ticker.symbol}"
            )

        points: list[PricePoint] = []

        for timestamp_raw, price_raw in zip(
            timestamps,
            prices,
            strict=True,
        ):
            # Yahoo может вернуть null для отдельного торгового дня.
            if price_raw is None:
                continue

            if isinstance(timestamp_raw, bool) or not isinstance(timestamp_raw, int):
                raise MarketDataResponseError(
                    f"Ответ для {request.ticker.symbol} содержит некорректную временную метку"
                )

            if isinstance(price_raw, bool) or not isinstance(
                price_raw,
                (int, float, str),
            ):
                raise MarketDataResponseError(
                    f"Ответ для {request.ticker.symbol} содержит некорректную цену"
                )

            try:
                adjusted_close = Decimal(str(price_raw))
            except InvalidOperation as error:
                raise MarketDataResponseError(
                    f"Ответ для {request.ticker.symbol} содержит некорректную цену"
                ) from error

            if not adjusted_close.is_finite() or adjusted_close <= Decimal("0"):
                raise MarketDataResponseError(
                    f"Ответ для {request.ticker.symbol} содержит неположительную цену"
                )

            try:
                trading_date = datetime.fromtimestamp(
                    timestamp_raw,
                    tz=UTC,
                ).date()

                point = PricePoint(
                    trading_date=trading_date,
                    adjusted_close=adjusted_close,
                )

            except (
                OSError,
                OverflowError,
                ValueError,
            ) as error:
                raise MarketDataResponseError(
                    f"Ответ для {request.ticker.symbol} содержит некорректную точку цены"
                ) from error

            points.append(point)

        if not points:
            raise MarketDataResponseError(
                f"Yahoo Finance не вернул цены для {request.ticker.symbol}"
            )

        try:
            return PriceHistory(
                ticker=request.ticker,
                currency=currency_raw,
                points=tuple(points),
            )
        except ValueError as error:
            raise MarketDataResponseError(
                f"История цен для {request.ticker.symbol} не прошла проверку"
            ) from error

    @staticmethod
    def _to_unix_timestamp(value: date) -> int:
        moment = datetime.combine(
            value,
            time.min,
            tzinfo=UTC,
        )

        return int(moment.timestamp())

    @staticmethod
    def _require_mapping(
        value: object,
        field_name: str,
    ) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise MarketDataResponseError(f"Поле {field_name} имеет некорректный формат")

        return cast(Mapping[str, object], value)

    @staticmethod
    def _require_list(
        value: object,
        field_name: str,
    ) -> list[object]:
        if not isinstance(value, list):
            raise MarketDataResponseError(f"Поле {field_name} имеет некорректный формат")

        return cast(list[object], value)
