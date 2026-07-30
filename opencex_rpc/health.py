"""Health checker and circuit-breaker logic."""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from .models import CircuitState, ProviderConfig, ProviderHealth

log = logging.getLogger("opencex_rpc.health")


class HealthRegistry:
    """
    Tracks health of all providers.
    Thread-safe enough for typical Django/Celery usage
    (GIL + atomic attribute updates). For multi-process use Redis later.
    """

    def __init__(self) -> None:
        self._health: Dict[str, ProviderHealth] = {}

    def _key(self, name: str, chain_id: int) -> str:
        return f"{chain_id}:{name}"

    def get_or_create(self, provider: ProviderConfig) -> ProviderHealth:
        key = self._key(provider.name, provider.chain_id)
        if key not in self._health:
            self._health[key] = ProviderHealth(
                name=provider.name,
                chain_id=provider.chain_id,
            )
        return self._health[key]

    def record_success(self, provider: ProviderConfig, latency_ms: float) -> None:
        h = self.get_or_create(provider)
        h.record_success(latency_ms)
        log.debug(
            "RPC OK  %s chain=%s latency=%.0fms score=%.1f",
            provider.name,
            provider.chain_id,
            latency_ms,
            h.score,
        )

    def record_error(
        self,
        provider: ProviderConfig,
        error_msg: str,
    ) -> None:
        h = self.get_or_create(provider)
        h.record_error(error_msg, provider.max_errors, provider.recovery_timeout)
        log.warning(
            "RPC ERR %s chain=%s errors=%s state=%s msg=%s",
            provider.name,
            provider.chain_id,
            h.consecutive_errors,
            h.state.value,
            error_msg[:120],
        )

    def is_available(self, provider: ProviderConfig) -> bool:
        h = self.get_or_create(provider)
        h.maybe_half_open(provider.recovery_timeout)
        return h.state != CircuitState.OPEN

    def rank_providers(
        self,
        providers: List[ProviderConfig],
    ) -> List[ProviderConfig]:
        """
        Return providers sorted by score (best first).
        Skips OPEN circuits.
        """
        scored = []
        for p in providers:
            h = self.get_or_create(p)
            h.maybe_half_open(p.recovery_timeout)
            if h.state == CircuitState.OPEN:
                continue
            # Combine health score with static weight & priority
            combined = h.score * (p.weight / 100.0) - (p.priority * 0.1)
            scored.append((combined, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def snapshot(self, chain_id: Optional[int] = None) -> List[dict]:
        result = []
        for h in self._health.values():
            if chain_id is not None and h.chain_id != chain_id:
                continue
            result.append(
                {
                    "name": h.name,
                    "chain_id": h.chain_id,
                    "state": h.state.value,
                    "avg_latency_ms": round(h.avg_latency_ms, 1),
                    "last_latency_ms": round(h.last_latency_ms, 1),
                    "error_rate": round(h.error_rate, 4),
                    "total_requests": h.total_requests,
                    "total_errors": h.total_errors,
                    "score": round(h.score, 2),
                    "last_error": h.last_error_msg,
                }
            )
        return sorted(result, key=lambda x: (-x["score"], x["name"]))


# Global singleton (process-local)
health_registry = HealthRegistry()
