"""Django REST endpoints for ZK-KYC."""

from __future__ import annotations

import logging

from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KYCProvider, VerificationLevel
from .service import KYCService

log = logging.getLogger("opencex_kyc.api")
_svc = None


def get_kyc_service() -> KYCService:
    global _svc
    if _svc is None:
        _svc = KYCService()
    return _svc


class StartVerificationSerializer(serializers.Serializer):
    level = serializers.ChoiceField(
        choices=[e.value for e in VerificationLevel],
        default=VerificationLevel.ZK_KYC.value,
    )
    provider = serializers.ChoiceField(
        choices=[e.value for e in KYCProvider if e != KYCProvider.SUMSUB],
        required=False,
    )


class KYCStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = StartVerificationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        level = VerificationLevel(v["level"])
        provider = KYCProvider(v["provider"]) if v.get("provider") else None
        session = get_kyc_service().start_verification(
            str(request.user.id), level=level, provider=provider
        )
        return Response({
            "session_id": session.session_id,
            "provider": session.provider.value,
            "level": session.level.value,
            "access_token": session.access_token,
            "app_id": session.app_id,
            "widget_config": session.widget_config,
            "auth_request": session.auth_request,
        })


class KYCStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rec = get_kyc_service().get_status(str(request.user.id))
        return Response({
            "user_id": rec.user_id,
            "status": rec.status.value,
            "level": rec.level.value if rec.level else None,
            "provider": rec.provider.value if rec.provider else None,
            "claims": rec.claims,
            "verified_at": rec.verified_at.isoformat() if rec.verified_at else None,
            "is_verified": rec.status.value == "approved",
        })


class KYCRefreshView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider")
        session_id = request.data.get("session_id")
        p = KYCProvider(provider) if provider else None
        rec = get_kyc_service().refresh_from_provider(
            str(request.user.id), provider=p, session_id=session_id
        )
        return Response({
            "status": rec.status.value,
            "level": rec.level.value if rec.level else None,
            "claims": rec.claims,
            "is_verified": rec.status.value == "approved",
        })


class KYCWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider: str):
        try:
            p = KYCProvider(provider.lower())
        except ValueError:
            return Response({"error": "unknown provider"}, status=400)
        headers = {k: v for k, v in request.headers.items()}
        rec = get_kyc_service().apply_webhook(
            p, request.data if isinstance(request.data, dict) else {}, headers
        )
        if not rec:
            return Response({"ok": True, "applied": False})
        return Response({
            "ok": True,
            "applied": True,
            "user_id": rec.user_id,
            "status": rec.status.value,
        })


class KYCProvidersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        svc = get_kyc_service()
        return Response({
            "primary": svc.primary.value,
            "available": [p.value for p in svc.providers.keys()],
        })
