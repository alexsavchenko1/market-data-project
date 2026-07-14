from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ticker:
    symbol: str

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Тикер не может быть пустым")

        object.__setattr__(self, "symbol", normalized_symbol)