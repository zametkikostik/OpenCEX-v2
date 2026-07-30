"""
REST views for OpenCEX Swap API.

  GET/POST  /api/v1/swap/preview/
  POST      /api/v1/swap/quote/
  POST      /api/v1/swap/execute/
  GET       /api/v1/swap/tokens/
  GET       /api/v1/swap/sources/
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from opencex_liquidity.client import ZeroXClient, ZeroXError
from opencex_liquidity.django_integration import InstantSwapService
from opencex_liquidity.tokens import TOKENS, get_token_map, resolve_token

from .serializers import (
    SUPPORTED_CHAINS,
    SwapExecuteSerializer,
    SwapPreviewSerializer,
    SwapQuoteSerializer,
)

log = logging.getLogger("opencex_swap_api")


def _error_response(exc: Exception, default_status: int = 400) -> Response:
    if isinstance(exc, ZeroXError):
        code = exc.status if exc.status >= 400 else default_status
        return Response(
            {"error": str(exc), "detail": exc.body},
            status=min(code, 599) if code else default_status,
        )
    if isinstance(exc, KeyError):
        return Response({"error": f"Unknown token: {exc}"}, status=400)
    log.exception("Swap API error")
    return Response({"error": str(exc)}, status=default_status)


class SwapPreviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "chain_id": request.query_params.get("chain_id", 1),
            "sell": request.query_params.get("sell"),
            "buy": request.query_params.get("buy"),
            "amount": request.query_params.get("amount"),
            "taker": request.query_params.get("taker") or "",
        }
        return self._handle(data)

    def post(self, request):
        return self._handle(request.data)

    def _handle(self, data: Any) -> Response:
        ser = SwapPreviewSerializer(data=data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            svc = InstantSwapService()
            result = svc.preview(
                chain_id=v["chain_id"],
                sell=v["sell"],
                buy=v["buy"],
                amount_wei=v["amount"],
                taker=v.get("taker") or None,
            )
            return Response(result)
        except Exception as exc:
            return _error_response(exc)


class SwapQuoteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = SwapQuoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            svc = InstantSwapService()
            result = svc.quote(
                chain_id=v["chain_id"],
                sell=v["sell"],
                buy=v["buy"],
                amount_wei=v["amount"],
                taker=v["taker"],
            )
            result["slippage_bps"] = v.get("slippage_bps", 100)
            return Response(result)
        except Exception as exc:
            return _error_response(exc)


class SwapExecuteView(APIView):
    """Custodial execute plan. Requires auth. Wire keeper signing in production."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SwapExecuteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        user = request.user

        try:
            chain_id = v["chain_id"]
            sell_token = resolve_token(chain_id, v["sell"])
            buy_token = resolve_token(chain_id, v["buy"])
            keeper_address = self._get_keeper_address(chain_id)
            if not keeper_address:
                return Response(
                    {"error": "Keeper not configured for this chain"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            svc = InstantSwapService()
            quote_data = svc.quote(
                chain_id=chain_id,
                sell=v["sell"],
                buy=v["buy"],
                amount_wei=v["amount"],
                taker=keeper_address,
            )

            plan = {
                "status": "pending_execution",
                "user_id": getattr(user, "id", None),
                "client_order_id": v.get("client_order_id"),
                "chain_id": chain_id,
                "sell_token": sell_token,
                "buy_token": buy_token,
                "sell_amount": v["amount"],
                "expected_buy_amount": quote_data.get("buy_amount"),
                "min_buy_amount": quote_data.get("min_buy_amount"),
                "needs_allowance": quote_data.get("needs_allowance"),
                "allowance_spender": quote_data.get("allowance_spender"),
                "transaction": quote_data.get("transaction"),
                "sources": quote_data.get("sources"),
                "zid": quote_data.get("zid"),
                "message": (
                    "Quote ready. Hook into keeper: lock balance, sign tx, "
                    "broadcast via opencex_rpc, credit buy token."
                ),
            }
            return Response(plan, status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _error_response(exc)

    def _get_keeper_address(self, chain_id: int):
        import os
        mapping = {
            1: os.getenv("ETH_KEEPER_ADDRESS") or os.getenv("ETH_SAFE_ADDR"),
            56: os.getenv("BNB_KEEPER_ADDRESS") or os.getenv("BNB_SAFE_ADDR"),
            137: os.getenv("MATIC_KEEPER_ADDRESS") or os.getenv("MATIC_SAFE_ADDR"),
            42161: os.getenv("ARB_KEEPER_ADDRESS"),
            8453: os.getenv("BASE_KEEPER_ADDRESS"),
        }
        return mapping.get(chain_id) or None


class SwapTokensView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        chain_id = request.query_params.get("chain_id")
        if chain_id:
            try:
                cid = int(chain_id)
            except ValueError:
                return Response({"error": "invalid chain_id"}, status=400)
            return Response({"chain_id": cid, "tokens": get_token_map(cid)})
        return Response({
            "chains": SUPPORTED_CHAINS,
            "tokens": {str(k): v for k, v in TOKENS.items()},
        })


class SwapSourcesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        chain_id = int(request.query_params.get("chain_id", 1))
        if chain_id not in SUPPORTED_CHAINS:
            return Response(
                {"error": f"Unsupported chain_id. Allowed: {SUPPORTED_CHAINS}"},
                status=400,
            )
        try:
            client = ZeroXClient()
            sources = client.list_sources(chain_id)
            return Response({"chain_id": chain_id, "sources": sources})
        except Exception as exc:
            return _error_response(exc)
