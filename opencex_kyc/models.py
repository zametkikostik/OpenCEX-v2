"""ZK-KYC domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class KYCProvider(str, Enum):
    ZKME = "zkme"
    ZKPASS = "zkpass"
    PRIVADO = "privado"
    SUMSUB = "sumsub"


class KYCStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class VerificationLevel(str, Enum):
    ME_ID = "meid"
    ZK_KYC = "zkkyc"
    AML = "aml"
    EXISTING_KYC = "existing"


@dataclass
class VerificationSession:
    session_id: str
    provider: KYCProvider
    level: VerificationLevel
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    app_id: Optional[str] = None
    widget_config: Dict[str, Any] = field(default_factory=dict)
    auth_request: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    user_id: str
    provider: KYCProvider
    level: VerificationLevel
    status: KYCStatus
    claims: Dict[str, Any] = field(default_factory=dict)
    credential_id: Optional[str] = None
    proof_hash: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        return self.status == KYCStatus.APPROVED


@dataclass
class UserKYCRecord:
    user_id: str
    status: KYCStatus = KYCStatus.NONE
    level: Optional[VerificationLevel] = None
    provider: Optional[KYCProvider] = None
    claims: Dict[str, Any] = field(default_factory=dict)
    credential_id: Optional[str] = None
    proof_hash: Optional[str] = None
    verified_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    providers_history: List[Dict[str, Any]] = field(default_factory=list)
