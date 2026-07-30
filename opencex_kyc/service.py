"""Unified KYC service – routes to zkMe / zkPass / Privado."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import (
    KYCProvider,
    KYCStatus,
    UserKYCRecord,
    VerificationLevel,
    VerificationResult,
    VerificationSession,
)
from .providers import PrivadoProvider, ZkMeProvider, ZkPassProvider
from .providers.base import BaseKYCProvider

log = logging.getLogger("opencex_kyc.service")


class InMemoryStore:
    def __init__(self):
        self._records: Dict[str, UserKYCRecord] = {}

    def get(self, user_id: str) -> Optional[UserKYCRecord]:
        return self._records.get(str(user_id))

    def save(self, record: UserKYCRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        self._records[str(record.user_id)] = record


class KYCService:
    def __init__(self, primary: Optional[str] = None, store: Optional[Any] = None):
        self.store = store or InMemoryStore()
        self.providers: Dict[KYCProvider, BaseKYCProvider] = {}

        if os.getenv("ZKME_API_KEY"):
            self.providers[KYCProvider.ZKME] = ZkMeProvider()
        if os.getenv("ZKPASS_API_KEY"):
            self.providers[KYCProvider.ZKPASS] = ZkPassProvider()
        if os.getenv("PRIVADO_VERIFIER_URL"):
            self.providers[KYCProvider.PRIVADO] = PrivadoProvider()

        if KYCProvider.ZKME not in self.providers:
            self.providers[KYCProvider.ZKME] = ZkMeProvider()
        if KYCProvider.ZKPASS not in self.providers:
            self.providers[KYCProvider.ZKPASS] = ZkPassProvider()
        if KYCProvider.PRIVADO not in self.providers:
            self.providers[KYCProvider.PRIVADO] = PrivadoProvider()

        primary_name = (primary or os.getenv("KYC_PRIMARY_PROVIDER", "zkme")).lower()
        self.primary = {
            "zkme": KYCProvider.ZKME,
            "zkpass": KYCProvider.ZKPASS,
            "privado": KYCProvider.PRIVADO,
        }.get(primary_name, KYCProvider.ZKME)

    def _provider(self, name: Optional[KYCProvider] = None) -> BaseKYCProvider:
        key = name or self.primary
        if key not in self.providers:
            raise ValueError(f"Provider {key} not configured")
        return self.providers[key]

    def start_verification(
        self,
        user_id: str,
        level: VerificationLevel = VerificationLevel.ZK_KYC,
        provider: Optional[KYCProvider] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationSession:
        prov = self._provider(provider)
        session = prov.start_session(str(user_id), level, metadata)
        rec = self.store.get(str(user_id)) or UserKYCRecord(user_id=str(user_id))
        if rec.status in (KYCStatus.NONE, KYCStatus.REJECTED, KYCStatus.EXPIRED):
            rec.status = KYCStatus.PENDING
            rec.provider = session.provider
            rec.level = level
            self.store.save(rec)
        return session

    def get_status(self, user_id: str) -> UserKYCRecord:
        rec = self.store.get(str(user_id))
        if rec:
            return rec
        return UserKYCRecord(user_id=str(user_id), status=KYCStatus.NONE)

    def refresh_from_provider(
        self,
        user_id: str,
        provider: Optional[KYCProvider] = None,
        session_id: Optional[str] = None,
    ) -> UserKYCRecord:
        result = self._provider(provider).get_status(str(user_id), session_id)
        return self._apply_result(result)

    def apply_webhook(
        self,
        provider: KYCProvider,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[UserKYCRecord]:
        result = self._provider(provider).handle_webhook(payload, headers)
        if not result:
            return None
        return self._apply_result(result)

    def _apply_result(self, result: VerificationResult) -> UserKYCRecord:
        rec = self.store.get(result.user_id) or UserKYCRecord(user_id=result.user_id)
        rec.status = result.status
        rec.level = result.level
        rec.provider = result.provider
        rec.claims = result.claims
        rec.credential_id = result.credential_id
        rec.proof_hash = result.proof_hash
        if result.verified_at:
            rec.verified_at = result.verified_at
        rec.providers_history.append({
            "provider": result.provider.value,
            "status": result.status.value,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self.store.save(rec)
        log.info("KYC updated user=%s provider=%s status=%s", result.user_id, result.provider.value, result.status.value)
        return rec

    def is_verified(self, user_id: str, min_level: Optional[VerificationLevel] = None) -> bool:
        rec = self.get_status(user_id)
        if rec.status != KYCStatus.APPROVED:
            return False
        if min_level == VerificationLevel.ZK_KYC and rec.level == VerificationLevel.ME_ID:
            return False
        return True
