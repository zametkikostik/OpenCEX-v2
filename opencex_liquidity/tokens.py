"""Common token addresses per chain for OpenCEX pairs."""

from __future__ import annotations

from typing import Dict

NATIVE = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

TOKENS: Dict[int, Dict[str, str]] = {
    1: {
        "ETH": NATIVE,
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954eedeAC495271d0F",
    },
    56: {
        "BNB": NATIVE,
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    },
    137: {
        "MATIC": NATIVE,
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDC.e": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    },
    42161: {
        "ETH": NATIVE,
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    },
    8453: {
        "ETH": NATIVE,
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0xfde4C96c8593536E31F7877A883BE7B392aC1F7B",
    },
}


def resolve_token(chain_id: int, symbol_or_address: str) -> str:
    s = symbol_or_address.strip()
    if s.startswith("0x") and len(s) == 42:
        return s
    chain_tokens = TOKENS.get(chain_id) or {}
    key = s.upper()
    if key not in chain_tokens:
        raise KeyError(f"Unknown token '{symbol_or_address}' on chain {chain_id}")
    return chain_tokens[key]


def get_token_map(chain_id: int) -> Dict[str, str]:
    return dict(TOKENS.get(chain_id) or {})
