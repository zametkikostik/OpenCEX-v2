"""zkMe provider – primary ZK-KYC. Docs: https://docs.zk.me API: https://openapi.zk.me"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from ..models import KYCProvider, KYCStatus, VerificationLevel, VerificationResult, VerificationSession
from .base import BaseKYCProvider

log = logging.getLogger("opencex_kyc.zkme")

LEVEL_MAP = {
    VerificationLevel.ME_ID: 2,
    VerificationLevel.ZK_KYC: 1,
    VerificationLevel.AML: 1,
}


class ZkMeProvider(BaseKYCProvider):
    name = KYCProvider.ZKME

    def __init__(self, api_key=None, app_id=None, base_url=None, timeout=20.0):
        self.api_key = api_key or os.getenv("ZKME_API_KEY", "")
        self.app_id = app_id or os.getenv("ZKME_APP_ID", "")
        self.base_url = (base_url or os.getenv("ZKME_API_BASE", "https://openapi.zk.me")).rstrip("/")
        self.timeout = timeout
        if not self.api_key or not self.app_id:
            log.warning("ZKME_API_KEY / ZKME_APP_ID not set")

    def _headers(self):
        return {"Content-Type": "application/json", "api_key": self.api_key, "mch_no": self.app_id}

    def _post(self, path, body):
        resp = requests.post(f"{self.base_url}{path}", json=body, headers=self._headers(), timeout=self.timeout)
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400 or (isinstance(data, dict) and data.get("code") not in (200, 0, None)):
            raise RuntimeError(f"zkMe API error: {data.get('message', data)}")
        return data.get("data", data) if isinstance(data, dict) else data

    def _get(self, path, params=None):
        resp = requests.get(f"{self.base_url}{path}", params=params or {}, headers=self._headers(), timeout=self.timeout)
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise RuntimeError(f"zkMe API error: {data}")
        return data.get("data", data) if isinstance(data, dict) else data

    def get_access_token(self, level=VerificationLevel.ZK_KYC):
        data = self._post("/api/token", {
            "apiKey": self.api_key,
            "appId": self.app_id,
            "lv": LEVEL_MAP.get(level, 1),
        })
        token = data.get("accessToken") or data.get("token") or data.get("access_token")
        if not token:
            if isinstance(data, str):
                return data
            raise RuntimeError(f"zkMe token missing: {data}")
        return token

    def start_session(self, user_id, level, metadata=None):
        session_id = str(uuid.uuid4())
        try:
            access_token = self.get_access_token(level)
        except Exception as exc:
            log.warning("zkMe token failed: %s", exc)
            access_token = None
        lv_name = "zkKYC" if level != VerificationLevel.ME_ID else "MeID"
        return VerificationSession(
            session_id=session_id,
            provider=KYCProvider.ZKME,
            level=level,
            user_id=str(user_id),
            access_token=access_token,
            app_id=self.app_id,
            widget_config={"appId": self.app_id, "lv": lv_name, "userId": str(user_id), **(metadata or {})},
        )

    def get_status(self, user_id, session_id=None):
        try:
            data = self._get("/api/kyc/status", params={"userId": str(user_id), "mch_no": self.app_id})
        except Exception as exc:
            return VerificationResult(
                user_id=str(user_id), provider=KYCProvider.ZKME, level=VerificationLevel.ZK_KYC,
                status=KYCStatus.NONE, raw={"error": str(exc)},
            )
        status_raw = str(data.get("status") or data.get("kycStatus") or "").lower()
        status_map = {
            "approved": KYCStatus.APPROVED, "pass": KYCStatus.APPROVED, "success": KYCStatus.APPROVED,
            "verified": KYCStatus.APPROVED, "pending": KYCStatus.PENDING, "processing": KYCStatus.IN_PROGRESS,
            "rejected": KYCStatus.REJECTED, "fail": KYCStatus.REJECTED, "failed": KYCStatus.REJECTED,
        }
        status = status_map.get(status_raw, KYCStatus.PENDING if status_raw else KYCStatus.NONE)
        claims = {}
        if data.get("isHuman") or data.get("meid"):
            claims["is_human"] = True
        if data.get("country"):
            claims["country"] = data["country"]
        if data.get("amlClear") is not None:
            claims["aml_clear"] = bool(data["amlClear"])
        return VerificationResult(
            user_id=str(user_id), provider=KYCProvider.ZKME, level=VerificationLevel.ZK_KYC,
            status=status, claims=claims,
            credential_id=data.get("credentialId") or data.get("certId"),
            verified_at=datetime.now(timezone.utc) if status == KYCStatus.APPROVED else None,
            raw=data if isinstance(data, dict) else {"data": data},
        )

    def handle_webhook(self, payload, headers=None):
        user_id = str(payload.get("userId") or payload.get("user_id") or "")
        if not user_id:
            return None
        return self.get_status(user_id)
