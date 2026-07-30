"""
Multi-provider RPC Router.

Usage:
    from opencex_rpc import get_web3

    w3 = get_web3(chain_id=1)          # Ethereum
    block = w3.eth.block_number
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.providers import HTTPProvider

from .config import get_chain, get_providers_for_chain
from .health import health_registry
from .models import ProviderConfig

log = logging.getLogger("opencex_rpc.router")


class ResilientHTTPProvider(HTTPProvider):
    """HTTPProvider that reports latency/errors to health registry."""

    def __init__(self, provider_cfg: ProviderConfig, *args, **kwargs):
        request_kwargs = kwargs.pop("request_kwargs", {}) or {}
        request_kwargs.setdefault("timeout", provider_cfg.timeout)
        if provider_cfg.headers:
            request_kwargs.setdefault("headers", {})
            request_kwargs["headers"].update(provider_cfg.headers)

        super().__init__(provider_cfg.url, request_kwargs=request_kwargs, *args, **kwargs)
        self.provider_cfg = provider_cfg

    def make_request(self, method, params):
        start = time.perf_counter()
        try:
            result = super().make_request(method, params)
            latency_ms = (time.perf_counter() - start) * 1000
            if isinstance(result, dict) and result.get("error"):
                health_registry.record_error(
                    self.provider_cfg,
                    str(result["error"]),
                )
            else:
                health_registry.record_success(self.provider_cfg, latency_ms)
            return result
        except Exception as exc:
            health_registry.record_error(self.provider_cfg, str(exc))
            raise


class MultiProviderRouter:
    """
    Selects the best available provider for a chain and returns a Web3 instance.
    Automatically fails over on errors.
    """

    def __init__(self) -> None:
        self._clients: Dict[int, Web3] = {}
        self._current_provider: Dict[int, ProviderConfig] = {}

    def get_web3(self, chain_id: int, force_refresh: bool = False) -> Web3:
        if not force_refresh and chain_id in self._clients:
            current = self._current_provider.get(chain_id)
            if current and health_registry.is_available(current):
                return self._clients[chain_id]

        return self._build_client(chain_id)

    def _build_client(self, chain_id: int) -> Web3:
        chain = get_chain(chain_id)
        providers = get_providers_for_chain(chain_id)

        if not providers:
            raise RuntimeError(
                f"No RPC providers configured for chain_id={chain_id}. "
                "Set DRPC_API_KEY / ANKR_API_KEY / RPC_ETH_URLS etc."
            )

        ranked = health_registry.rank_providers(providers)
        if not ranked:
            log.error("All providers OPEN for chain %s – forcing recovery", chain_id)
            ranked = sorted(providers, key=lambda p: (-p.weight, p.priority))

        last_error: Optional[Exception] = None

        for provider in ranked:
            try:
                w3 = self._create_web3(provider, chain.is_poa)
                _ = w3.eth.block_number
                self._clients[chain_id] = w3
                self._current_provider[chain_id] = provider
                log.info(
                    "RPC bound: chain=%s (%s) → %s",
                    chain_id,
                    chain.name,
                    provider.name,
                )
                return w3
            except Exception as exc:
                last_error = exc
                health_registry.record_error(provider, str(exc))
                log.warning(
                    "Provider %s failed for chain %s: %s",
                    provider.name,
                    chain_id,
                    exc,
                )
                continue

        raise RuntimeError(
            f"All RPC providers failed for chain_id={chain_id}. Last error: {last_error}"
        )

    def _create_web3(self, provider: ProviderConfig, is_poa: bool) -> Web3:
        http_provider = ResilientHTTPProvider(provider)
        w3 = Web3(http_provider)
        if is_poa:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return w3

    def failover(self, chain_id: int) -> Web3:
        """Force switch to next best provider."""
        current = self._current_provider.get(chain_id)
        if current:
            health_registry.record_error(current, "manual_failover")
        return self.get_web3(chain_id, force_refresh=True)

    def health_snapshot(self, chain_id: Optional[int] = None) -> List[dict]:
        return health_registry.snapshot(chain_id)

    def current_provider_name(self, chain_id: int) -> Optional[str]:
        p = self._current_provider.get(chain_id)
        return p.name if p else None


router = MultiProviderRouter()


def get_web3(chain_id: int = 1) -> Web3:
    """Public drop-in helper."""
    return router.get_web3(chain_id)
