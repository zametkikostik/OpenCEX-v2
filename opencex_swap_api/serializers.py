"""Request/response serializers for swap API (Django REST Framework)."""

from __future__ import annotations

from rest_framework import serializers

SUPPORTED_CHAINS = [1, 56, 137, 42161, 8453]


class SwapPreviewSerializer(serializers.Serializer):
    chain_id = serializers.IntegerField(default=1)
    sell = serializers.CharField(max_length=64, help_text="Token symbol or address")
    buy = serializers.CharField(max_length=64)
    amount = serializers.CharField(help_text="Sell amount in wei")
    taker = serializers.CharField(required=False, allow_blank=True, max_length=42)

    def validate_chain_id(self, value):
        if value not in SUPPORTED_CHAINS:
            raise serializers.ValidationError(f"Unsupported chain_id. Allowed: {SUPPORTED_CHAINS}")
        return value

    def validate_amount(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("amount must be integer string (wei)")
        if n <= 0:
            raise serializers.ValidationError("amount must be positive")
        return str(n)


class SwapQuoteSerializer(serializers.Serializer):
    chain_id = serializers.IntegerField(default=1)
    sell = serializers.CharField(max_length=64)
    buy = serializers.CharField(max_length=64)
    amount = serializers.CharField()
    taker = serializers.CharField(max_length=42)
    slippage_bps = serializers.IntegerField(required=False, default=100, min_value=1, max_value=5000)

    def validate_chain_id(self, value):
        if value not in SUPPORTED_CHAINS:
            raise serializers.ValidationError(f"Unsupported chain_id. Allowed: {SUPPORTED_CHAINS}")
        return value

    def validate_amount(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("amount must be integer string (wei)")
        if n <= 0:
            raise serializers.ValidationError("amount must be positive")
        return str(n)

    def validate_taker(self, value):
        v = value.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise serializers.ValidationError("taker must be a valid 0x address")
        return v


class SwapExecuteSerializer(serializers.Serializer):
    chain_id = serializers.IntegerField(default=1)
    sell = serializers.CharField(max_length=64)
    buy = serializers.CharField(max_length=64)
    amount = serializers.CharField()
    slippage_bps = serializers.IntegerField(required=False, default=100, min_value=1, max_value=5000)
    client_order_id = serializers.CharField(required=False, max_length=64, allow_blank=True)

    def validate_chain_id(self, value):
        if value not in SUPPORTED_CHAINS:
            raise serializers.ValidationError(f"Unsupported chain_id. Allowed: {SUPPORTED_CHAINS}")
        return value

    def validate_amount(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("amount must be integer string (wei)")
        if n <= 0:
            raise serializers.ValidationError("amount must be positive")
        return str(n)
