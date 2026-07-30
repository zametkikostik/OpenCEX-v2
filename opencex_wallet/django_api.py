"""REST API for Hybrid Wallet."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WalletMode
from .service import HybridWalletService

_svc = None


def get_wallet_service():
    global _svc
    if _svc is None:
        _svc = HybridWalletService()
    return _svc


class SessionSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=[m.value for m in WalletMode])
    address = serializers.CharField(required=False, allow_blank=True, max_length=42)
    chain_id = serializers.IntegerField(default=1)


class OrderBuildSerializer(serializers.Serializer):
    chain_id = serializers.IntegerField(default=1)
    sell_token = serializers.CharField(max_length=42)
    buy_token = serializers.CharField(max_length=42)
    sell_amount = serializers.CharField()
    min_buy_amount = serializers.CharField()
    trader = serializers.CharField(max_length=42)
    expiry_sec = serializers.IntegerField(default=600, min_value=60, max_value=86400)


class OrderSubmitSerializer(serializers.Serializer):
    typed_data = serializers.DictField()
    signature = serializers.CharField()
    mode = serializers.ChoiceField(
        choices=[m.value for m in WalletMode], default=WalletMode.NON_CUSTODIAL.value
    )


class NCSwapSerializer(serializers.Serializer):
    chain_id = serializers.IntegerField(default=1)
    sell_token = serializers.CharField()
    buy_token = serializers.CharField()
    sell_amount = serializers.CharField()
    taker = serializers.CharField(max_length=42)


class WalletSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SessionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        session = get_wallet_service().create_session(
            user_id=str(request.user.id),
            mode=WalletMode(v["mode"]),
            address=v.get("address") or None,
            chain_id=v["chain_id"],
        )
        return Response({
            "session_id": session.session_id,
            "mode": session.mode.value,
            "address": session.address,
            "chain_id": session.chain_id,
        })


class OrderBuildView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = OrderBuildSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        typed = get_wallet_service().build_order_typed_data(**{
            k: v[k] for k in (
                "chain_id", "trader", "sell_token", "buy_token",
                "sell_amount", "min_buy_amount", "expiry_sec",
            )
        })
        return Response({"typed_data": typed})


class OrderSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = OrderSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            order = get_wallet_service().submit_signed_order(
                user_id=str(request.user.id),
                typed_data=v["typed_data"],
                signature=v["signature"],
                mode=WalletMode(v["mode"]),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({
            "order_id": order.order_id,
            "status": order.status,
            "signer": order.signer,
            "sell_amount": order.sell_amount,
            "buy_token": order.buy_token,
        })


class NonCustodialSwapView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = NCSwapSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            return Response(get_wallet_service().prepare_zerox_for_user(**v))
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)
