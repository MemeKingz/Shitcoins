from typing import TypedDict


class DexMetric(TypedDict):
    total_fdv: float
    fdv_count: int
    liquidity: float
    price: float
    token_name: str