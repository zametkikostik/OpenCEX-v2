"""
High-level convenience client and chain constants.

Drop-in replacements for the old OpenCEX helpers:
    from opencex_rpc import w3_eth, w3_bnb, get_web3
"""

from __future__ import annotations

from web3 import Web3

from .router import get_web3, router

# Chain IDs
ETH = 1
BNB = 56
POLYGON = 137
ARBITRUM = 42161
BASE = 8453

CHAIN_NAMES = {
    ETH: "ethereum",
    BNB: "bsc",
    POLYGON: "polygon",
    ARBITRUM: "arbitrum",
    BASE: "base",
}


def w3_eth() -> Web3:
    return get_web3(ETH)


def w3_bnb() -> Web3:
    return get_web3(BNB)


def w3_polygon() -> Web3:
    return get_web3(POLYGON)


def w3_arbitrum() -> Web3:
    return get_web3(ARBITRUM)


def w3_base() -> Web3:
    return get_web3(BASE)


def failover(chain_id: int) -> Web3:
    return router.failover(chain_id)


def health(chain_id: int | None = None) -> list[dict]:
    return router.health_snapshot(chain_id)
