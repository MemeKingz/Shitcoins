from typing import TypedDict, List

from shitcoins.holder import Holder


class CoinData(TypedDict):
    coin_address: str
    holders: List[Holder]
