"""Abstract KYC provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..models import KYCProvider, VerificationLevel, VerificationResult, VerificationSession


class BaseKYCProvider(ABC):
    name: KYCProvider

    @abstractmethod
    def start_session(
        self,
        user_id: str,
        level: VerificationLevel,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationSession:
        ...

    @abstractmethod
    def get_status(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> VerificationResult:
        ...

    @abstractmethod
    def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[VerificationResult]:
        ...

    def health_check(self) -> bool:
        return True
