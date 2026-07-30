from django.contrib import admin
from .models import SignedOrderRecord, SwapExecution, UserKYC, WalletSessionRecord


@admin.register(UserKYC)
class UserKYCAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "level", "provider", "verified_at", "updated_at")
    list_filter = ("status", "provider", "level")
    search_fields = ("user__username", "user__email", "credential_id")
    readonly_fields = ("created_at", "updated_at", "history")


@admin.register(WalletSessionRecord)
class WalletSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "address", "chain_id", "is_active", "created_at")
    list_filter = ("mode", "is_active", "chain_id")
    search_fields = ("address", "session_id", "user__username")


@admin.register(SignedOrderRecord)
class SignedOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "signer", "status", "chain_id", "created_at")
    list_filter = ("status", "chain_id")
    search_fields = ("order_id", "signer", "fill_tx_hash")


@admin.register(SwapExecution)
class SwapExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "sell_symbol", "buy_symbol", "status", "tx_hash", "created_at")
    list_filter = ("status", "chain_id")
    search_fields = ("tx_hash", "client_order_id", "user__username")
    readonly_fields = ("plan", "created_at", "updated_at")
