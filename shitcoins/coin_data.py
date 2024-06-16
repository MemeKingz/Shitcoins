from typing import TypedDict, List

from shitcoins.holder import Holder

from shitcoins.model.market_info import MarketInfo


class CoinData(TypedDict):
    coin_address: str
    market_info: MarketInfo
    holders: List[Holder]
