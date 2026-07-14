from pathlib import Path

from market_data.ticker_reader import generate_tickers


def main() -> None:
    ticker_file = Path("config/tickers.csv")

    for ticker in generate_tickers(ticker_file):
        print(ticker.symbol)


if __name__ == "__main__":
    main()