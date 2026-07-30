"""
0x Swap API v2 client.

Docs: https://docs.0x.org
Base URL: https://api.0x.org
Headers: 0x-api-key, 0x-version: v2
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from .models import LiquiditySource, SwapPrice, SwapQuote

log = logging.getLogger("opencex_liquidity.client")

ZEROX_BASE = os.getenv("ZEROX_API_BASE", "https://api.0x.org")
ZEROX_VERSION = "v2"
NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"


class ZeroXError(Exception):
    def __init__(self, message: str, status: int = 0, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class ZeroXClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 15.0,
        approval_model: str = "allowance-holder",
    ):
        self.api_key = api_key or os.getenv("ZEROX_API_KEY", "")
        if not self.api_key:
            log.warning("ZEROX_API_KEY not set – requests will fail")
        self.timeout = timeout
        if approval_model not in ("allowance-holder", "permit2"):
            raise ValueError("approval_model must be 'allowance-holder' or 'permit2'")
        self.approval_model = approval_model
        self.session = requests.Session()
        self.session.headers.update(
            {
                "0x-api-key": self.api_key,
                "0x-version": ZEROX_VERSION,
                "Accept": "application/json",
            }
        )

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        clean = {k: v for k, v in params.items() if v is not None}
        url = f"{ZEROX_BASE}{path}?{urlencode(clean)}"
        log.debug("0x GET %s", url)
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ZeroXError(f"Network error: {exc}") from exc

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        if resp.status_code >= 400:
            msg = body.get("message") or body.get("reason") or str(body) if isinstance(body, dict) else str(body)
            raise ZeroXError(f"0x API {resp.status_code}: {msg}", status=resp.status_code, body=body)

        return body if isinstance(body, dict) else {"raw": body}

    def _parse_sources(self, raw: Dict[str, Any]) -> List[LiquiditySource]:
        sources = []
        for s in raw.get("sources") or raw.get("route", {}).get("fills") or []:
            if isinstance(s, dict):
                name = s.get("name") or s.get("source") or "unknown"
                prop = float(s.get("proportion") or s.get("proportionBps", 0) / 10000 or 0)
                sources.append(LiquiditySource(name=name, proportion=prop))
        return sources

    def get_price(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: Optional[str] = None,
        slippage_bps: int = 100,
        swap_fee_bps: Optional[int] = None,
        swap_fee_recipient: Optional[str] = None,
        swap_fee_token: Optional[str] = None,
    ) -> SwapPrice:
        path = f"/swap/{self.approval_model}/price"
        params: Dict[str, Any] = {
            "chainId": chain_id,
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": sell_amount,
            "slippageBps": slippage_bps,
        }
        if taker:
            params["taker"] = taker
        if swap_fee_bps and swap_fee_recipient:
            params["swapFeeBps"] = swap_fee_bps
            params["swapFeeRecipient"] = swap_fee_recipient
            if swap_fee_token:
                params["swapFeeToken"] = swap_fee_token

        data = self._get(path, params)
        return SwapPrice(
            chain_id=chain_id,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=data.get("sellAmount") or sell_amount,
            buy_amount=str(data.get("buyAmount", "0")),
            price=str(data.get("price") or data.get("grossPrice") or "0"),
            estimated_gas=str(data["gas"]) if data.get("gas") else None,
            sources=self._parse_sources(data),
            raw=data,
        )

    def get_quote(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: str,
        slippage_bps: int = 100,
        swap_fee_bps: Optional[int] = None,
        swap_fee_recipient: Optional[str] = None,
        swap_fee_token: Optional[str] = None,
        trade_surplus_recipient: Optional[str] = None,
        tx_origin: Optional[str] = None,
    ) -> SwapQuote:
        path = f"/swap/{self.approval_model}/quote"
        params: Dict[str, Any] = {
            "chainId": chain_id,
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": sell_amount,
            "taker": taker,
            "slippageBps": slippage_bps,
        }
        if swap_fee_bps and swap_fee_recipient:
            params["swapFeeBps"] = swap_fee_bps
            params["swapFeeRecipient"] = swap_fee_recipient
            if swap_fee_token:
                params["swapFeeToken"] = swap_fee_token
        if trade_surplus_recipient:
            params["tradeSurplusRecipient"] = trade_surplus_recipient
        if tx_origin:
            params["txOrigin"] = tx_origin

        data = self._get(path, params)
        tx = data.get("transaction") or data
        issues = data.get("issues") or {}

        return SwapQuote(
            chain_id=chain_id,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=str(data.get("sellAmount") or sell_amount),
            buy_amount=str(data.get("buyAmount", "0")),
            price=str(data.get("price") or data.get("grossPrice") or "0"),
            min_buy_amount=str(data["minBuyAmount"]) if data.get("minBuyAmount") else None,
            estimated_gas=str(tx.get("gas") or data.get("gas") or "") or None,
            to=tx.get("to"),
            data=tx.get("data"),
            value=str(tx["value"]) if tx.get("value") is not None else "0",
            gas=str(tx["gas"]) if tx.get("gas") else None,
            gas_price=str(tx["gasPrice"]) if tx.get("gasPrice") else None,
            allowance_target=data.get("allowanceTarget") or (issues.get("allowance") or {}).get("spender"),
            issues=issues,
            sources=self._parse_sources(data),
            fees=data.get("fees") or {},
            zid=data.get("zid"),
            raw=data,
        )

    def get_gasless_quote(
        self,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: str,
        slippage_bps: int = 100,
        **fee_kwargs,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "chainId": chain_id,
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": sell_amount,
            "taker": taker,
            "slippageBps": slippage_bps,
            **{k: v for k, v in fee_kwargs.items() if v is not None},
        }
        return self._get("/gasless/quote", params)

    def list_sources(self, chain_id: int) -> List[str]:
        data = self._get("/sources", {"chainId": chain_id})
        sources = data.get("sources") or data.get("liquiditySources") or []
        if isinstance(sources, list) and sources and isinstance(sources[0], dict):
            return [s.get("name", str(s)) for s in sources]
        return list(sources)


_default_client: Optional[ZeroXClient] = None


def _client() -> ZeroXClient:
    global _default_client
    if _default_client is None:
        _default_client = ZeroXClient()
    return _default_client


def get_swap_price(
    chain_id: int,
    sell_token: str,
    buy_token: str,
    sell_amount: str,
    taker: Optional[str] = None,
    **kwargs,
) -> SwapPrice:
    return _client().get_price(chain_id, sell_token, buy_token, sell_amount, taker=taker, **kwargs)


def get_swap_quote(
    chain_id: int,
    sell_token: str,
    buy_token: str,
    sell_amount: str,
    taker: str,
    **kwargs,
) -> SwapQuote:
    return _client().get_quote(chain_id, sell_token, buy_token, sell_amount, taker, **kwargs)
