from __future__ import annotations
import logging, os
from dataclasses import dataclass
from typing import List, Optional
log = logging.getLogger("opencex_risk.circuit")

@dataclass
class CircuitBreaker:
    halted: bool; chains: List[int]; reason: str
    def blocks(self, chain_id: int) -> bool:
        return self.halted or chain_id in self.chains

def load_breaker() -> CircuitBreaker:
    chains = [int(x) for x in os.getenv("OPENCEX_CIRCUIT_BREAKER_CHAINS", "").split(",") if x.strip().isdigit()]
    return CircuitBreaker(os.getenv("OPENCEX_CIRCUIT_BREAKER", "0") == "1", chains,
                          os.getenv("OPENCEX_CIRCUIT_BREAKER_REASON", "manual"))

def is_trading_halted(chain_id: Optional[int] = None) -> bool:
    b = load_breaker()
    return b.halted if chain_id is None else b.blocks(chain_id)

def assert_can_swap(chain_id: int) -> None:
    b = load_breaker()
    if b.blocks(chain_id):
        raise RuntimeError(f"trading_halted:{b.reason}")
