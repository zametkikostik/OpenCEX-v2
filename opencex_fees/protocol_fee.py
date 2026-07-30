from __future__ import annotations
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple

@dataclass
class ProtocolFeeConfig:
    fee_bps: int = 5
    recipient: str = ""
    enabled: bool = True
    max_bps: int = 100
    def clamp(self):
        self.fee_bps = max(0, min(self.fee_bps, self.max_bps))
        return self

def load_fee_config():
    return ProtocolFeeConfig(
        fee_bps=int(os.getenv("PROTOCOL_FEE_BPS", "5")),
        recipient=os.getenv("PROTOCOL_TREASURY") or os.getenv("FEE_RECIPIENT") or "",
        enabled=os.getenv("PROTOCOL_FEE_ENABLED", "1") == "1",
    ).clamp()

def apply_fee_to_amount(amount_wei, fee_bps=None):
    cfg = load_fee_config()
    bps = fee_bps if fee_bps is not None else cfg.fee_bps
    if not cfg.enabled or bps <= 0:
        return str(amount_wei), "0"
    amt = Decimal(str(amount_wei))
    fee = (amt * Decimal(bps)) // Decimal(10000)
    return str(int(amt - fee)), str(int(fee))
