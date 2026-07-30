"""Async swap execute + status poll."""

from __future__ import annotations

import logging
import os

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from opencex_liquidity.django_integration import InstantSwapService
from opencex_liquidity.tokens import resolve_token
from opencex_swap_api.serializers import SwapExecuteSerializer
from .tasks import enqueue_swap

log = logging.getLogger("opencex_django.execute")


class SwapExecuteAsyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SwapExecuteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        chain_id = v["chain_id"]
        keeper_map = {
            1: os.getenv("ETH_KEEPER_ADDRESS") or os.getenv("ETH_SAFE_ADDR"),
            56: os.getenv("BNB_KEEPER_ADDRESS") or os.getenv("BNB_SAFE_ADDR"),
            137: os.getenv("MATIC_KEEPER_ADDRESS") or os.getenv("MATIC_SAFE_ADDR"),
            42161: os.getenv("ARB_KEEPER_ADDRESS"),
            8453: os.getenv("BASE_KEEPER_ADDRESS"),
        }
        keeper = keeper_map.get(chain_id)
        if not keeper:
            return Response({"error": "Keeper not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            sell_token = resolve_token(chain_id, v["sell"])
            buy_token = resolve_token(chain_id, v["buy"])
            quote = InstantSwapService().quote(
                chain_id=chain_id, sell=v["sell"], buy=v["buy"],
                amount_wei=v["amount"], taker=keeper,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)

        plan = {
            "chain_id": chain_id,
            "sell_token": sell_token,
            "buy_token": buy_token,
            "sell_amount": v["amount"],
            "expected_buy_amount": quote.get("buy_amount"),
            "min_buy_amount": quote.get("min_buy_amount"),
            "needs_allowance": quote.get("needs_allowance"),
            "allowance_spender": quote.get("allowance_spender"),
            "transaction": quote.get("transaction"),
            "sources": quote.get("sources"),
            "zid": quote.get("zid"),
        }
        execution = enqueue_swap(
            user=request.user, plan=plan,
            sell_symbol=v["sell"], buy_symbol=v["buy"],
            client_order_id=v.get("client_order_id"),
        )
        return Response({
            "status": execution.status,
            "execution_id": execution.id,
            "celery_task_id": execution.celery_task_id,
            "expected_buy_amount": execution.expected_buy_amount,
            "message": "Swap queued. Poll GET /api/v1/swap/execution/<id>/",
        }, status=status.HTTP_202_ACCEPTED)


class SwapExecutionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, execution_id: int):
        from opencex_django.models import SwapExecution
        try:
            ex = SwapExecution.objects.get(pk=execution_id, user=request.user)
        except SwapExecution.DoesNotExist:
            return Response({"error": "not_found"}, status=404)
        return Response({
            "execution_id": ex.id,
            "status": ex.status,
            "tx_hash": ex.tx_hash,
            "block_number": ex.block_number,
            "sell_symbol": ex.sell_symbol,
            "buy_symbol": ex.buy_symbol,
            "sell_amount": ex.sell_amount,
            "expected_buy_amount": ex.expected_buy_amount,
            "actual_buy_amount": ex.actual_buy_amount,
            "error": ex.error,
            "created_at": ex.created_at.isoformat(),
            "updated_at": ex.updated_at.isoformat(),
        })
