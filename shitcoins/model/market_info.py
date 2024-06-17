from typing import TypedDict


class MarketInfo(TypedDict):
    token_name: str
    market_cap: float
    liquidity: float
    price: float