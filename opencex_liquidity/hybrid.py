"""
Hybrid Liquidity Router

Combines:
  1. Internal OpenCEX orderbook (custodial matching)
  2. 0x aggregated DEX liquidity

Strategy:
  - Small / liquid pairs → prefer internal book
  - Large size or thin book → route fully or partially via 0x
  - Instant Swap UI → always 0x
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .client import ZeroXClient
from .models import SwapQuote, SwapPrice

log = logging.getLogger("opencex_liquidity.hybrid")


class RouteDecision(str, Enum):
    INTERNAL = "internal"
    ZEROX = "zerox"
    SPLIT = "split"


@dataclass
class RouteResult:
    decision: RouteDecision
    internal_amount: Decimal = Decimal("0")
    zerox_amount: Decimal = Decimal("0")
    zerox_quote: Optional[SwapQuote] = None
    zerox_price: Optional[SwapPrice] = None
    reason: str = ""
    meta: Dict[str, Any] = None

    def __post_init__(self):
        if self.meta is None:
            self.meta = {}


class HybridLiquidityRouter:
    def __init__(
        self,
        zerox: Optional[ZeroXClient] = None,
        internal_max_usd: Optional[Decimal] = None,
        split_ratio: Optional[float] = None,
        slippage_bps: int = 100,
        fee_bps: Optional[int] = None,
        fee_recipient: Optional[str] = None,
        internal_liquidity_fn: Optional[Callable[..., Decimal]] = None,
        usd_value_fn: Optional[Callable[..., Decimal]] = None,
    ):
        self.zerox = zerox or ZeroXClient()
        self.internal_max_usd = internal_max_usd or Decimal(
            os.getenv("HYBRID_INTERNAL_MAX_USD", "5000")
        )
        self.split_ratio = split_ratio if split_ratio is not None else float(
            os.getenv("HYBRID_SPLIT_RATIO", "0.6")
        )
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps if fee_bps is not None else (
            int(os.getenv("ZEROX_FEE_BPS", "0")) or None
        )
        self.fee_recipient = fee_recipient or os.getenv("ZEROX_FEE_RECIPIENT") or None
        self.internal_liquidity_fn = internal_liquidity_fn
        self.usd_value_fn = usd_value_fn

    def _fee_kwargs(self, sell_token: str) -> Dict[str, Any]:
        if self.fee_bps and self.fee_recipient:
            return {
                "swap_fee_bps": self.fee_bps,
                "swap_fee_recipient": self.fee_recipient,
                "swap_fee_token": sell_token,
            }
        return {}

    def route_instant_swap(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: str,
        force_zerox: bool = True,
    ) -> RouteResult:
        if force_zerox or self.internal_liquidity_fn is None:
            quote = self.zerox.get_quote(
                chain_id=chain_id,
                sell_token=sell_token,
                buy_token=buy_token,
                sell_amount=sell_amount,
                taker=taker,
                slippage_bps=self.slippage_bps,
                **self._fee_kwargs(sell_token),
            )
            return RouteResult(
                decision=RouteDecision.ZEROX,
                zerox_amount=Decimal(sell_amount),
                zerox_quote=quote,
                reason="instant_swap_via_0x",
            )
        return self.route_order(chain_id, sell_token, buy_token, sell_amount, taker)

    def route_order(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: str,
        pair: Optional[str] = None,
    ) -> RouteResult:
        amount = Decimal(sell_amount)
        internal_available = Decimal("0")
        if self.internal_liquidity_fn and pair:
            try:
                internal_available = Decimal(
                    str(self.internal_liquidity_fn(pair, "buy", amount))
                )
            except Exception as exc:
                log.warning("internal_liquidity_fn failed: %s", exc)

        usd_value = Decimal("0")
        if self.usd_value_fn:
            try:
                usd_value = self.usd_value_fn(sell_token, sell_amount, amount)
            except Exception:
                pass

        if internal_available >= amount and (
            usd_value <= self.internal_max_usd or usd_value == 0
        ):
            return RouteResult(
                decision=RouteDecision.INTERNAL,
                internal_amount=amount,
                reason="full_internal_liquidity",
            )

        if internal_available <= 0:
            quote = self.zerox.get_quote(
                chain_id=chain_id,
                sell_token=sell_token,
                buy_token=buy_token,
                sell_amount=sell_amount,
                taker=taker,
                slippage_bps=self.slippage_bps,
                **self._fee_kwargs(sell_token),
            )
            return RouteResult(
                decision=RouteDecision.ZEROX,
                zerox_amount=amount,
                zerox_quote=quote,
                reason="no_internal_liquidity",
            )

        internal_fill = min(internal_available, amount * Decimal(str(self.split_ratio)))
        zerox_fill = amount - internal_fill
        if zerox_fill <= 0:
            return RouteResult(
                decision=RouteDecision.INTERNAL,
                internal_amount=amount,
                reason="split_collapsed_to_internal",
            )

        quote = self.zerox.get_quote(
            chain_id=chain_id,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=str(int(zerox_fill)),
            taker=taker,
            slippage_bps=self.slippage_bps,
            **self._fee_kwargs(sell_token),
        )
        return RouteResult(
            decision=RouteDecision.SPLIT,
            internal_amount=internal_fill,
            zerox_amount=zerox_fill,
            zerox_quote=quote,
            reason="hybrid_split",
            meta={"internal_available": str(internal_available)},
        )

    def get_indicative_price(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: Optional[str] = None,
    ) -> SwapPrice:
        return self.zerox.get_price(
            chain_id=chain_id,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=sell_amount,
            taker=taker,
            slippage_bps=self.slippage_bps,
            **self._fee_kwargs(sell_token),
        )
