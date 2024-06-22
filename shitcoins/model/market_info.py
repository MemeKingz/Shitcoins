from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class MarketInfo(TypedDict):
    token_name: str
    market_cap: float
    liquidity: float
    price: float
    created_at_utc: datetime | None