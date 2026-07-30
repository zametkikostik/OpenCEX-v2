"""Core data models for OpenCEX RPC Router."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing, do not use
    HALF_OPEN = "half_open" # testing recovery


@dataclass
class ProviderConfig:
    """Static configuration of a single RPC endpoint."""

    name: str
    url: str
    chain_id: int
    weight: int = 100          # higher = preferred when healthy
    timeout: float = 8.0
    max_errors: int = 5        # errors before opening circuit
    recovery_timeout: float = 30.0  # seconds before half-open
    headers: dict = field(default_factory=dict)
    is_websocket: bool = False
    priority: int = 50         # lower = higher priority on equal score


@dataclass
class ProviderHealth:
    """Runtime health state of a provider."""

    name: str
    chain_id: int
    state: CircuitState = CircuitState.CLOSED
    consecutive_errors: int = 0
    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    last_latency_ms: float = 0.0
    last_success_at: Optional[float] = None
    last_error_at: Optional[float] = None
    last_error_msg: Optional[str] = None
    opened_at: Optional[float] = None

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 9999.0
        return self.total_latency_ms / max(self.total_requests - self.total_errors, 1)

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests

    @property
    def score(self) -> float:
        """
        Higher score = better provider.
        Combines latency, error rate and circuit state.
        """
        if self.state == CircuitState.OPEN:
            return -1.0
        if self.state == CircuitState.HALF_OPEN:
            return 10.0  # allow limited probing

        # Base score from inverse latency (prefer faster)
        latency_score = 1000.0 / max(self.avg_latency_ms, 1.0)
        error_penalty = self.error_rate * 500.0
        return max(latency_score - error_penalty, 0.0)

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        self.last_latency_ms = latency_ms
        self.last_success_at = time.time()
        self.consecutive_errors = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.opened_at = None

    def record_error(self, error_msg: str, max_errors: int, recovery_timeout: float) -> None:
        now = time.time()
        self.total_requests += 1
        self.total_errors += 1
        self.consecutive_errors += 1
        self.last_error_at = now
        self.last_error_msg = error_msg[:500]

        if self.consecutive_errors >= max_errors:
            self.state = CircuitState.OPEN
            self.opened_at = now

    def maybe_half_open(self, recovery_timeout: float) -> bool:
        """Transition OPEN → HALF_OPEN when recovery window elapsed."""
        if self.state != CircuitState.OPEN:
            return False
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at >= recovery_timeout:
            self.state = CircuitState.HALF_OPEN
            self.consecutive_errors = 0
            return True
        return False


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""

    chain_id: int
    name: str
    symbol: str
    is_poa: bool = False          # needs geth_poa_middleware
    block_time_sec: float = 12.0
    native_decimals: int = 18
