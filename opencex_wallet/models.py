"""Hybrid wallet domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class WalletMode(str, Enum):
    CUSTODIAL = "custodial"
    NON_CUSTODIAL = "non_custodial"
    HYBRID = "hybrid"


@dataclass
class WalletSession:
    user_id: str
    mode: WalletMode
    address: Optional[str] = None
    chain_id: int = 1
    session_id: str = ""
    created_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignedOrder:
    order_id: str
    user_id: str
    chain_id: int
    sell_token: str
    buy_token: str
    sell_amount: str
    min_buy_amount: str
    nonce: int
    expiry: int
    signature: str
    signer: str
    mode: WalletMode = WalletMode.NON_CUSTODIAL
    status: str = "open"
    raw: Dict[str, Any] = field(default_factory=dict)
