"""Basic tests – run with: pytest tests/ -v"""

from __future__ import annotations

import os
import pytest

# Force public RPCs for tests so CI works without keys
os.environ.setdefault("USE_PUBLIC_RPCS", "true")
os.environ.setdefault("USE_1RPC", "true")


def test_import():
    from opencex_rpc import get_web3, health, ETH, BNB
    assert ETH == 1
    assert BNB == 56


def test_providers_loaded():
    from opencex_rpc.config import get_providers_for_chain
    eth_providers = get_providers_for_chain(1)
    assert len(eth_providers) >= 1


@pytest.mark.integration
def test_eth_block_number():
    """Requires network access."""
    from opencex_rpc import get_web3
    w3 = get_web3(1)
    block = w3.eth.block_number
    assert isinstance(block, int)
    assert block > 0


@pytest.mark.integration
def test_health_snapshot():
    from opencex_rpc import get_web3, health
    get_web3(1)  # warm up
    snap = health(1)
    assert isinstance(snap, list)
