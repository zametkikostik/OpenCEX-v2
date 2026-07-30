"""Data models for 0x liquidity layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class LiquiditySource:
    name: str
    proportion: float


@dataclass
class SwapPrice:
    chain_id: int
    sell_token: str
    buy_token: str
    sell_amount: str
    buy_amount: str
    price: str
    estimated_gas: Optional[str] = None
    sources: List[LiquiditySource] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def sell_amount_decimal(self) -> Decimal:
        return Decimal(self.sell_amount)

    @property
    def buy_amount_decimal(self) -> Decimal:
        return Decimal(self.buy_amount)


@dataclass
class SwapQuote:
    chain_id: int
    sell_token: str
    buy_token: str
    sell_amount: str
    buy_amount: str
    price: str
    min_buy_amount: Optional[str] = None
    estimated_gas: Optional[str] = None
    to: Optional[str] = None
    data: Optional[str] = None
    value: Optional[str] = None
    gas: Optional[str] = None
    gas_price: Optional[str] = None
    allowance_target: Optional[str] = None
    issues: Dict[str, Any] = field(default_factory=dict)
    sources: List[LiquiditySource] = field(default_factory=list)
    fees: Dict[str, Any] = field(default_factory=dict)
    zid: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def needs_allowance(self) -> bool:
        allowance = self.issues.get("allowance")
        if not allowance:
            return False
        actual = allowance.get("actual", "0")
        return str(actual) == "0" or int(actual) == 0

    @property
    def allowance_spender(self) -> Optional[str]:
        allowance = self.issues.get("allowance") or {}
        return allowance.get("spender") or self.allowance_target

    def to_tx_dict(self) -> Dict[str, Any]:
        tx: Dict[str, Any] = {}
        if self.to:
            tx["to"] = self.to
        if self.data:
            tx["data"] = self.data
        if self.value is not None:
            tx["value"] = int(self.value)
        if self.gas:
            tx["gas"] = int(self.gas)
        if self.gas_price:
            tx["gasPrice"] = int(self.gas_price)
        tx["chainId"] = self.chain_id
        return tx
