from __future__ import annotations
import logging
from typing import Optional
log = logging.getLogger("opencex_django.permissions")
try:
    from rest_framework.permissions import BasePermission
except ImportError:
    class BasePermission:
        def has_permission(self, request, view):
            return True

def _gates():
    try:
        from django.conf import settings
        return getattr(settings, "OPENCEX_KYC_GATES", {}) or {}
    except Exception:
        return {}

def user_kyc_verified(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        from opencex_django.models import UserKYC
        kyc = UserKYC.objects.filter(user=user).first()
        if kyc and getattr(kyc, "is_verified", False):
            return True
        if kyc and str(getattr(kyc, "status", "")).lower() in ("approved", "verified", "passed"):
            return True
    except Exception as exc:
        log.debug("kyc lookup: %s", exp)
    return False

class IsKYCVerified(BasePermission):
    message = "ZK-KYC verification required."
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return user_kyc_verified(request.user)

class KYCRequiredForWithdraw(BasePermission):
    message = "KYC required for withdrawals."
    def has_permission(self, request, view) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if not _gates().get("require_for_withdraw", True):
            return True
        return user_kyc_verified(request.user)

def kyc_required_for_swap_amount(estimated_usd: Optional[float]) -> bool:
    threshold = float(_gates().get("require_for_custodial_swap_above_usd") or 0)
    if threshold <= 0 or estimated_usd is None:
        return False
    return float(estimated_usd) >= threshold
