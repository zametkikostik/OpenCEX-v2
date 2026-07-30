"""Django models: UserKYC, WalletSession, SignedOrder, SwapExecution."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserKYC(models.Model):
    class Status(models.TextChoices):
        NONE = "none", "None"
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    class Level(models.TextChoices):
        ME_ID = "meid", "MeID"
        ZK_KYC = "zkkyc", "zkKYC"
        AML = "aml", "AML"
        EXISTING = "existing", "Existing KYC"

    class Provider(models.TextChoices):
        ZKME = "zkme", "zkMe"
        ZKPASS = "zkpass", "zkPass"
        PRIVADO = "privado", "Privado ID"
        SUMSUB = "sumsub", "Sumsub"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="opencex_kyc")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NONE, db_index=True)
    level = models.CharField(max_length=32, choices=Level.choices, null=True, blank=True)
    provider = models.CharField(max_length=32, choices=Provider.choices, null=True, blank=True)
    claims = models.JSONField(default=dict, blank=True)
    credential_id = models.CharField(max_length=255, null=True, blank=True)
    proof_hash = models.CharField(max_length=255, null=True, blank=True)
    session_id = models.CharField(max_length=64, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User KYC"
        verbose_name_plural = "User KYC records"

    def __str__(self):
        return f"KYC({self.user_id}, {self.status})"

    @property
    def is_verified(self) -> bool:
        return self.status == self.Status.APPROVED

    def apply_result(self, status, provider=None, level=None, claims=None, credential_id=None, proof_hash=None):
        self.status = status
        if provider:
            self.provider = provider
        if level:
            self.level = level
        if claims is not None:
            self.claims = claims
        if credential_id:
            self.credential_id = credential_id
        if proof_hash:
            self.proof_hash = proof_hash
        if status == self.Status.APPROVED:
            self.verified_at = timezone.now()
        hist = list(self.history or [])
        hist.append({"status": status, "provider": provider, "at": timezone.now().isoformat()})
        self.history = hist[-50:]
        self.save()


class WalletSessionRecord(models.Model):
    class Mode(models.TextChoices):
        CUSTODIAL = "custodial", "Custodial"
        NON_CUSTODIAL = "non_custodial", "Non-Custodial"
        HYBRID = "hybrid", "Hybrid"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_sessions")
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    mode = models.CharField(max_length=32, choices=Mode.choices)
    address = models.CharField(max_length=42, null=True, blank=True, db_index=True)
    chain_id = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SignedOrderRecord(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        FILLED = "filled", "Filled"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signed_orders")
    order_id = models.CharField(max_length=64, unique=True, db_index=True)
    chain_id = models.PositiveIntegerField()
    sell_token = models.CharField(max_length=42)
    buy_token = models.CharField(max_length=42)
    sell_amount = models.CharField(max_length=78)
    min_buy_amount = models.CharField(max_length=78)
    nonce = models.PositiveIntegerField()
    expiry = models.PositiveIntegerField()
    signature = models.TextField()
    signer = models.CharField(max_length=42, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN, db_index=True)
    typed_data = models.JSONField(default=dict, blank=True)
    fill_tx_hash = models.CharField(max_length=66, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SwapExecution(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        LOCKING = "locking", "Locking"
        BROADCASTING = "broadcasting", "Broadcasting"
        CONFIRMING = "confirming", "Confirming"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REVERTED = "reverted", "Reverted"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="swap_executions")
    client_order_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    chain_id = models.PositiveIntegerField()
    sell_symbol = models.CharField(max_length=32)
    buy_symbol = models.CharField(max_length=32)
    sell_token = models.CharField(max_length=42)
    buy_token = models.CharField(max_length=42)
    sell_amount = models.CharField(max_length=78)
    expected_buy_amount = models.CharField(max_length=78, null=True, blank=True)
    actual_buy_amount = models.CharField(max_length=78, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED, db_index=True)
    tx_hash = models.CharField(max_length=66, null=True, blank=True, db_index=True)
    block_number = models.PositiveBigIntegerField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    plan = models.JSONField(default=dict, blank=True)
    celery_task_id = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
