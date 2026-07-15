from pathlib import Path

import httpx

from market_data.exceptions import MarketDataError
from market_data.providers.yahoo import YahooFinanceProvider
from market_data.request_reader import (
    generate_price_history_requests,
)

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"


def main() -> None:
    # Пока обрабатываем только первый запрос из файла.
    request_file = Path("config/requests.csv")
    request = next(
        generate_price_history_requests(request_file),
        None,
    )

    if request is None:
        raise SystemExit("Файл не содержит запросов")

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    try:
        with httpx.Client(
            base_url=YAHOO_BASE_URL,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "market-data-project/0.1",
            },
        ) as client:
            provider = YahooFinanceProvider(client)
            history = provider.fetch_history(request)

    except MarketDataError as error:
        raise SystemExit(
            f"Не удалось получить котировки: {error}"
        ) from error

    print(f"Тикер: {history.ticker.symbol}")
    print(f"Валюта: {history.currency}")
    print(f"Количество точек: {len(history.points)}")
    print()

    for point in history.points:
        print(
            f"{point.trading_date}: "
            f"{point.adjusted_close}"
        )


if __name__ == "__main__":
    main()