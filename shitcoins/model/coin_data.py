from __future__ import annotations

from typing import TypedDict, List

from shitcoins.model.first_buy_statistics import FirstBuyStatistics
from shitcoins.model.holder import Holder

from shitcoins.model.market_info import MarketInfo


class CoinData(TypedDict):
    coin_address: str
    market_info: MarketInfo
    first_buy_statistics: FirstBuyStatistics | None
    holders: List[Holder]
