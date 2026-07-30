"""
OpenCEX Liquidity Layer
=======================

0x Protocol integration for deep DEX liquidity + hybrid routing.

Quick start:
    from opencex_liquidity import ZeroXClient, get_swap_quote

    client = ZeroXClient()
    quote = client.get_quote(
        chain_id=1,
        sell_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        buy_token="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        sell_amount="1000000000000000000",
        taker="0xYourAddress",
    )
"""

from .client import ZeroXClient, get_swap_quote, get_swap_price
from .models import SwapQuote, SwapPrice, LiquiditySource
from .hybrid import HybridLiquidityRouter

__all__ = [
    "ZeroXClient",
    "get_swap_quote",
    "get_swap_price",
    "SwapQuote",
    "SwapPrice",
    "LiquiditySource",
    "HybridLiquidityRouter",
]

__version__ = "0.1.0"
