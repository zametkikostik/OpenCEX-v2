"""
OpenCEX RPC Router
==================

Production-ready multi-provider RPC layer for OpenCEX.

Quick start:
    from opencex_rpc import get_web3, w3_eth, health

    w3 = get_web3(1)                 # Ethereum
    print(w3.eth.block_number)
"""

from .client import (
    ARBITRUM,
    BASE,
    BNB,
    ETH,
    POLYGON,
    failover,
    get_web3,
    health,
    w3_arbitrum,
    w3_base,
    w3_bnb,
    w3_eth,
    w3_polygon,
)
from .router import MultiProviderRouter, router

__all__ = [
    "get_web3",
    "w3_eth",
    "w3_bnb",
    "w3_polygon",
    "w3_arbitrum",
    "w3_base",
    "failover",
    "health",
    "router",
    "MultiProviderRouter",
    "ETH",
    "BNB",
    "POLYGON",
    "ARBITRUM",
    "BASE",
]

__version__ = "0.1.0"
