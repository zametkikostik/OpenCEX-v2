"""
Optional Django helpers for OpenCEX-backend integration.

Usage:
    from opencex_liquidity.django_integration import InstantSwapService

    svc = InstantSwapService()
    price = svc.preview(chain_id=1, sell="ETH", buy="USDT", amount_wei="1000000000000000000")
    quote = svc.quote(chain_id=1, sell="ETH", buy="USDT", amount_wei="...", taker=addr)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .client import ZeroXClient
from .hybrid import HybridLiquidityRouter, RouteResult
from .models import SwapPrice, SwapQuote
from .tokens import resolve_token

log = logging.getLogger("opencex_liquidity.django")


class InstantSwapService:
    """Service layer for OpenCEX Quick Swap UI. Always routes through 0x."""

    def __init__(self, zerox: Optional[ZeroXClient] = None):
        self.router = HybridLiquidityRouter(zerox=zerox)

    def preview(
        self,
        chain_id: int,
        sell: str,
        buy: str,
        amount_wei: str,
        taker: Optional[str] = None,
    ) -> Dict[str, Any]:
        sell_token = resolve_token(chain_id, sell)
        buy_token = resolve_token(chain_id, buy)
        price: SwapPrice = self.router.get_indicative_price(
            chain_id, sell_token, buy_token, amount_wei, taker=taker
        )
        return {
            "chain_id": chain_id,
            "sell_token": sell_token,
            "buy_token": buy_token,
            "sell_amount": price.sell_amount,
            "buy_amount": price.buy_amount,
            "price": price.price,
            "estimated_gas": price.estimated_gas,
            "sources": [{"name": s.name, "proportion": s.proportion} for s in price.sources],
        }

    def quote(
        self,
        chain_id: int,
        sell: str,
        buy: str,
        amount_wei: str,
        taker: str,
    ) -> Dict[str, Any]:
        sell_token = resolve_token(chain_id, sell)
        buy_token = resolve_token(chain_id, buy)
        result: RouteResult = self.router.route_instant_swap(
            chain_id, sell_token, buy_token, amount_wei, taker, force_zerox=True
        )
        q = result.zerox_quote
        if not q:
            raise RuntimeError("No 0x quote returned")

        return {
            "decision": result.decision.value,
            "chain_id": chain_id,
            "sell_token": sell_token,
            "buy_token": buy_token,
            "sell_amount": q.sell_amount,
            "buy_amount": q.buy_amount,
            "min_buy_amount": q.min_buy_amount,
            "price": q.price,
            "needs_allowance": q.needs_allowance,
            "allowance_spender": q.allowance_spender,
            "transaction": q.to_tx_dict(),
            "sources": [{"name": s.name, "proportion": s.proportion} for s in q.sources],
            "zid": q.zid,
        }
