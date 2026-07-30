"""zkPass – prove existing Web2 KYC via zkTLS. Docs: https://docs.zkpass.org"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..models import KYCProvider, KYCStatus, VerificationLevel, VerificationResult, VerificationSession
from .base import BaseKYCProvider

log = logging.getLogger("opencex_kyc.zkpass")


class ZkPassProvider(BaseKYCProvider):
    name = KYCProvider.ZKPASS

    def __init__(self, api_key=None, api_secret=None, schema_id=None, base_url=None, timeout=20.0):
        self.api_key = api_key or os.getenv("ZKPASS_API_KEY", "")
        self.api_secret = api_secret or os.getenv("ZKPASS_API_SECRET", "")
        self.schema_id = schema_id or os.getenv("ZKPASS_SCHEMA_ID", "")
        self.base_url = (base_url or os.getenv("ZKPASS_API_BASE", "https://api.zkpass.org")).rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            log.warning("ZKPASS_API_KEY not set")

    def start_session(self, user_id, level=VerificationLevel.EXISTING_KYC, metadata=None):
        session_id = str(uuid.uuid4())
        schema = (metadata or {}).get("schema_id") or self.schema_id
        return VerificationSession(
            session_id=session_id,
            provider=KYCProvider.ZKPASS,
            level=level,
            user_id=str(user_id),
            widget_config={
                "schemaId": schema,
                "userId": str(user_id),
                "appId": self.api_key[:8] if self.api_key else "",
            },
            raw={"schema_id": schema},
        )

    def get_status(self, user_id, session_id=None):
        if not session_id:
            return VerificationResult(
                user_id=str(user_id), provider=KYCProvider.ZKPASS,
                level=VerificationLevel.EXISTING_KYC, status=KYCStatus.NONE,
            )
        return VerificationResult(
            user_id=str(user_id), provider=KYCProvider.ZKPASS,
            level=VerificationLevel.EXISTING_KYC, status=KYCStatus.PENDING,
            raw={"session_id": session_id},
        )

    def verify_proof(self, user_id, proof_payload):
        if not proof_payload:
            return VerificationResult(
                user_id=str(user_id), provider=KYCProvider.ZKPASS,
                level=VerificationLevel.EXISTING_KYC, status=KYCStatus.REJECTED,
                rejection_reason="empty_proof",
            )
        task_id = proof_payload.get("taskId") or proof_payload.get("allocatorAddress")
        return VerificationResult(
            user_id=str(user_id), provider=KYCProvider.ZKPASS,
            level=VerificationLevel.EXISTING_KYC, status=KYCStatus.APPROVED,
            claims={"existing_kyc_proven": True, "source": proof_payload.get("schemaName") or "web2"},
            proof_hash=str(task_id) if task_id else None,
            verified_at=datetime.now(timezone.utc),
            raw=proof_payload,
        )

    def handle_webhook(self, payload, headers=None):
        user_id = str(payload.get("userId") or payload.get("user_id") or "")
        if not user_id:
            return None
        return self.verify_proof(user_id, payload)
