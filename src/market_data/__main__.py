from pathlib import Path

import httpx

from market_data.application.sequential import (
    fetch_histories_sequentially,
)
from market_data.providers.yahoo import YahooFinanceProvider
from market_data.request_reader import (
    generate_price_history_requests,
)

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"


def main() -> None:
    request_file = Path("config/requests.csv")
    requests = generate_price_history_requests(request_file)

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    with httpx.Client(
        base_url=YAHOO_BASE_URL,
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": "market-data-project/0.1",
        },
    ) as client:
        provider = YahooFinanceProvider(client)

        result = fetch_histories_sequentially(
            requests=requests,
            provider=provider,
        )

    print("Результаты последовательной загрузки")
    print("=" * 40)

    for history in result.histories:
        print(
            f"[УСПЕХ] {history.ticker.symbol}: "
            f"{len(history.points)} точек, "
            f"валюта {history.currency}"
        )

    for failure in result.failures:
        print(
            f"[ОШИБКА] {failure.ticker.symbol}: "
            f"{failure.message}"
        )

    print("=" * 40)
    print(f"Успешно: {len(result.histories)}")
    print(f"Ошибок: {len(result.failures)}")
    print(
        f"Общее время: "
        f"{result.elapsed_seconds:.3f} секунд"
    )


if __name__ == "__main__":
    main()