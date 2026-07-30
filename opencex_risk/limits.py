from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

@dataclass
class RiskLimits:
    max_swap_usd: float = 10000.0
    max_daily_usd_per_user: float = 50000.0
    max_notional_wei: Optional[int] = None
    allowed_tokens: Set[str] = field(default_factory=set)
    allowed_chains: List[int] = field(default_factory=lambda: [1, 56, 137, 42161, 8453])

def load_risk_limits() -> RiskLimits:
    tokens = os.getenv("RISK_ALLOWED_TOKENS", "ETH,USDT,USDC,BNB,MATIC,WETH,WBNB")
    max_wei = os.getenv("RISK_MAX_NOTIONAL_WEI")
    return RiskLimits(
        max_swap_usd=float(os.getenv("RISK_MAX_SWAP_USD", "10000")),
        max_daily_usd_per_user=float(os.getenv("RISK_MAX_DAILY_USD_PER_USER", "50000")),
        max_notional_wei=int(max_wei) if max_wei else None,
        allowed_tokens={t.strip().upper() for t in tokens.split(",") if t.strip()},
        allowed_chains=[int(x) for x in os.getenv("RISK_ALLOWED_CHAINS", "1,56,137,42161,8453").split(",") if x.strip().isdigit()],
    )

_daily_usd: dict = {}

def check_swap_risk(user_id, chain_id, sell_symbol, buy_symbol, sell_amount_wei, estimated_usd=None):
    limits = load_risk_limits()
    if chain_id not in limits.allowed_chains: return False, f"chain_blocked:{chain_id}"
    if limits.allowed_tokens:
        if sell_symbol.upper() not in limits.allowed_tokens: return False, f"sell_token_blocked:{sell_symbol}"
        if buy_symbol.upper() not in limits.allowed_tokens: return False, f"buy_token_blocked:{buy_symbol}"
    try: amt = int(sell_amount_wei)
    except Exception: return False, "invalid_amount"
    if limits.max_notional_wei is not None and amt > limits.max_notional_wei:
        return False, "exceeds_max_notional_wei"
    if estimated_usd is not None:
        if estimated_usd > limits.max_swap_usd: return False, f"exceeds_max_swap_usd:{limits.max_swap_usd}"
        import datetime as dt
        key = f"{user_id}:{dt.date.today().isoformat()}"
        used = float(_daily_usd.get(key, 0.0))
        if used + estimated_usd > limits.max_daily_usd_per_user:
            return False, f"exceeds_daily_usd:{limits.max_daily_usd_per_user}"
        _daily_usd[key] = used + estimated_usd
    return True, None
