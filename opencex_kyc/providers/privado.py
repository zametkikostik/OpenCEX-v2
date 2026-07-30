"""Privado ID (ex-Polygon ID) – W3C VC + ZK proofs. Docs: https://docs.privado.id"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from ..models import KYCProvider, KYCStatus, VerificationLevel, VerificationResult, VerificationSession
from .base import BaseKYCProvider

log = logging.getLogger("opencex_kyc.privado")


class PrivadoProvider(BaseKYCProvider):
    name = KYCProvider.PRIVADO

    def __init__(self, verifier_url=None, issuer_did=None, timeout=25.0):
        self.verifier_url = (verifier_url or os.getenv("PRIVADO_VERIFIER_URL", "")).rstrip("/")
        self.issuer_did = issuer_did or os.getenv("PRIVADO_ISSUER_DID", "")
        self.timeout = timeout
        if not self.verifier_url:
            log.warning("PRIVADO_VERIFIER_URL not set")

    def start_session(self, user_id, level=VerificationLevel.ZK_KYC, metadata=None):
        session_id = str(uuid.uuid4())
        auth_request = {
            "id": session_id,
            "thid": session_id,
            "typ": "application/iden3comm-plain-json",
            "type": "https://iden3-communication.io/authorization/1.0/request",
            "body": {
                "callbackUrl": (metadata or {}).get(
                    "callback_url",
                    f"{self.verifier_url}/api/v1/kyc/webhook/privado/",
                ),
                "reason": "OpenCEX KYC verification",
                "scope": (metadata or {}).get("scope") or [{
                    "circuitId": "credentialAtomicQuerySigV2",
                    "query": {
                        "allowedIssuers": ["*"],
                        "type": "KYCAgeCredential",
                        "context": "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v3.json-ld",
                    },
                }],
            },
            "from": self.issuer_did or "did:polygonid:polygon:main:verifier",
        }
        return VerificationSession(
            session_id=session_id,
            provider=KYCProvider.PRIVADO,
            level=level,
            user_id=str(user_id),
            auth_request=auth_request,
            widget_config={"sessionId": session_id, "userId": str(user_id)},
            raw={"auth_request": auth_request},
        )

    def get_status(self, user_id, session_id=None):
        if not self.verifier_url or not session_id:
            return VerificationResult(
                user_id=str(user_id), provider=KYCProvider.PRIVADO,
                level=VerificationLevel.ZK_KYC, status=KYCStatus.NONE,
            )
        try:
            resp = requests.get(f"{self.verifier_url}/status/{session_id}", timeout=self.timeout)
            data = resp.json() if resp.ok else {}
        except Exception as exc:
            log.warning("Privado status failed: %s", exc)
            data = {}
        verified = data.get("verified") or data.get("status") == "verified"
        return VerificationResult(
            user_id=str(user_id), provider=KYCProvider.PRIVADO,
            level=VerificationLevel.ZK_KYC,
            status=KYCStatus.APPROVED if verified else KYCStatus.PENDING,
            claims=data.get("claims") or {},
            verified_at=datetime.now(timezone.utc) if verified else None,
            raw=data,
        )

    def handle_webhook(self, payload, headers=None):
        user_id = str(payload.get("userId") or payload.get("user_id") or "unknown")
        ok = payload.get("verified") is True or payload.get("proof") is not None
        return VerificationResult(
            user_id=user_id, provider=KYCProvider.PRIVADO,
            level=VerificationLevel.ZK_KYC,
            status=KYCStatus.APPROVED if ok else KYCStatus.REJECTED,
            claims=payload.get("claims") or {"zk_proof_valid": ok},
            proof_hash=payload.get("proofId"),
            verified_at=datetime.now(timezone.utc) if ok else None,
            raw=payload,
        )
