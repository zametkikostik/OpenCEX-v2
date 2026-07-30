"""
Default configuration for supported chains and RPC providers.

Secrets (API keys) must come from environment variables.
Never hardcode keys in source.
"""

from __future__ import annotations

import os
from typing import Dict, List

from .models import ChainConfig, ProviderConfig


CHAINS: Dict[int, ChainConfig] = {
    1: ChainConfig(
        chain_id=1,
        name="ethereum",
        symbol="ETH",
        is_poa=False,
        block_time_sec=12.0,
    ),
    56: ChainConfig(
        chain_id=56,
        name="bsc",
        symbol="BNB",
        is_poa=True,
        block_time_sec=3.0,
    ),
    137: ChainConfig(
        chain_id=137,
        name="polygon",
        symbol="MATIC",
        is_poa=True,
        block_time_sec=2.0,
    ),
    42161: ChainConfig(
        chain_id=42161,
        name="arbitrum",
        symbol="ETH",
        is_poa=False,
        block_time_sec=0.25,
    ),
    8453: ChainConfig(
        chain_id=8453,
        name="base",
        symbol="ETH",
        is_poa=False,
        block_time_sec=2.0,
    ),
}


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _build_providers() -> List[ProviderConfig]:
    providers: List[ProviderConfig] = []

    def add(
        name: str,
        chain_id: int,
        url: str,
        weight: int = 100,
        priority: int = 50,
        headers: dict | None = None,
    ) -> None:
        if not url:
            return
        providers.append(
            ProviderConfig(
                name=name,
                url=url,
                chain_id=chain_id,
                weight=weight,
                priority=priority,
                headers=headers or {},
            )
        )

    drpc_key = _env("DRPC_API_KEY")
    if drpc_key:
        add("drpc-eth", 1, f"https://lb.drpc.org/ogrpc?network=ethereum&dkey={drpc_key}", weight=120, priority=10)
        add("drpc-bsc", 56, f"https://lb.drpc.org/ogrpc?network=bsc&dkey={drpc_key}", weight=120, priority=10)
        add("drpc-polygon", 137, f"https://lb.drpc.org/ogrpc?network=polygon&dkey={drpc_key}", weight=120, priority=10)
        add("drpc-arbitrum", 42161, f"https://lb.drpc.org/ogrpc?network=arbitrum&dkey={drpc_key}", weight=120, priority=10)
        add("drpc-base", 8453, f"https://lb.drpc.org/ogrpc?network=base&dkey={drpc_key}", weight=120, priority=10)

    ankr_key = _env("ANKR_API_KEY")
    if ankr_key:
        add("ankr-eth", 1, f"https://rpc.ankr.com/eth/{ankr_key}", weight=110, priority=20)
        add("ankr-bsc", 56, f"https://rpc.ankr.com/bsc/{ankr_key}", weight=110, priority=20)
        add("ankr-polygon", 137, f"https://rpc.ankr.com/polygon/{ankr_key}", weight=110, priority=20)
        add("ankr-arbitrum", 42161, f"https://rpc.ankr.com/arbitrum/{ankr_key}", weight=110, priority=20)
        add("ankr-base", 8453, f"https://rpc.ankr.com/base/{ankr_key}", weight=110, priority=20)

    lava_key = _env("LAVA_API_KEY")
    if lava_key:
        add("lava-eth", 1, f"https://eth1.lava.build/lava-referer-{lava_key}/", weight=100, priority=30)
        add("lava-bsc", 56, f"https://bsc.lava.build/lava-referer-{lava_key}/", weight=100, priority=30)
        add("lava-polygon", 137, f"https://polygon.lava.build/lava-referer-{lava_key}/", weight=100, priority=30)
        add("lava-arbitrum", 42161, f"https://arb1.lava.build/lava-referer-{lava_key}/", weight=100, priority=30)
        add("lava-base", 8453, f"https://base.lava.build/lava-referer-{lava_key}/", weight=100, priority=30)

    getblock_key = _env("GETBLOCK_API_KEY")
    if getblock_key:
        add("getblock-eth", 1, f"https://go.getblock.io/{getblock_key}", weight=100, priority=40)

    nownodes_key = _env("NOWNODES_API_KEY")
    if nownodes_key:
        add("nownodes-eth", 1, f"https://eth.nownodes.io/{nownodes_key}", weight=90, priority=50)
        add("nownodes-bsc", 56, f"https://bsc.nownodes.io/{nownodes_key}", weight=90, priority=50)
        add("nownodes-polygon", 137, f"https://matic.nownodes.io/{nownodes_key}", weight=90, priority=50)
        add("nownodes-arbitrum", 42161, f"https://arbitrum.nownodes.io/{nownodes_key}", weight=90, priority=50)
        add("nownodes-base", 8453, f"https://base.nownodes.io/{nownodes_key}", weight=90, priority=50)

    grove_app = _env("GROVE_APP_ID")
    grove_key = _env("GROVE_API_KEY")
    if grove_app:
        headers = {"Authorization": grove_key} if grove_key else {}
        add("grove-eth", 1, f"https://eth-mainnet.rpc.grove.city/v1/{grove_app}", weight=100, priority=25, headers=headers)
        add("grove-bsc", 56, f"https://bsc-mainnet.rpc.grove.city/v1/{grove_app}", weight=100, priority=25, headers=headers)
        add("grove-polygon", 137, f"https://poly-mainnet.rpc.grove.city/v1/{grove_app}", weight=100, priority=25, headers=headers)
        add("grove-arbitrum", 42161, f"https://arbitrum-one.rpc.grove.city/v1/{grove_app}", weight=100, priority=25, headers=headers)
        add("grove-base", 8453, f"https://base-mainnet.rpc.grove.city/v1/{grove_app}", weight=100, priority=25, headers=headers)

    use_1rpc = _env("USE_1RPC", "true").lower() in ("1", "true", "yes")
    if use_1rpc:
        add("1rpc-eth", 1, "https://1rpc.io/eth", weight=80, priority=60)
        add("1rpc-bsc", 56, "https://1rpc.io/bnb", weight=80, priority=60)
        add("1rpc-polygon", 137, "https://1rpc.io/matic", weight=80, priority=60)
        add("1rpc-arbitrum", 42161, "https://1rpc.io/arb", weight=80, priority=60)
        add("1rpc-base", 8453, "https://1rpc.io/base", weight=80, priority=60)

    use_public = _env("USE_PUBLIC_RPCS", "true").lower() in ("1", "true", "yes")
    if use_public:
        add("public-eth-cloudflare", 1, "https://cloudflare-eth.com", weight=30, priority=90)
        add("public-eth-llamarpc", 1, "https://eth.llamarpc.com", weight=30, priority=91)
        add("public-bsc", 56, "https://bsc-dataseed.binance.org", weight=30, priority=90)
        add("public-polygon", 137, "https://polygon-rpc.com", weight=30, priority=90)
        add("public-arbitrum", 42161, "https://arb1.arbitrum.io/rpc", weight=30, priority=90)
        add("public-base", 8453, "https://mainnet.base.org", weight=30, priority=90)

    chain_env_map = {
        1: "RPC_ETH_URLS",
        56: "RPC_BNB_URLS",
        137: "RPC_POLYGON_URLS",
        42161: "RPC_ARBITRUM_URLS",
        8453: "RPC_BASE_URLS",
    }
    for chain_id, env_key in chain_env_map.items():
        raw = _env(env_key)
        if not raw:
            continue
        for i, url in enumerate(u.strip() for u in raw.split(",") if u.strip()):
            add(f"custom-{chain_id}-{i}", chain_id, url, weight=130, priority=5)

    return providers


def get_providers() -> List[ProviderConfig]:
    return _build_providers()


def get_providers_for_chain(chain_id: int) -> List[ProviderConfig]:
    return [p for p in get_providers() if p.chain_id == chain_id]


def get_chain(chain_id: int) -> ChainConfig:
    if chain_id not in CHAINS:
        raise ValueError(f"Unsupported chain_id={chain_id}. Supported: {list(CHAINS)}")
    return CHAINS[chain_id]
