from typing import TypedDict, List


class CoinData(TypedDict):
    coin_address: str
    holders: List[str]
