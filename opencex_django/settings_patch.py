"""Drop-in settings for OpenCEX-backend: apply_opencex_v2(globals())."""
from __future__ import annotations
import os
from typing import Any, Dict

def apply_opencex_v2(g: Dict[str, Any]) -> None:
    apps = list(g.get("INSTALLED_APPS") or [])
    for app in ("opencex_django", "opencex_swap_api", "opencex_kyc", "opencex_wallet"):
        if app not in apps:
            apps.append(app)
    g["INSTALLED_APPS"] = apps
    imports = list(g.get("CELERY_IMPORTS") or [])
    if "opencex_django.tasks" not in imports:
        imports.append("opencex_django.tasks")
    g["CELERY_IMPORTS"] = imports
    try:
        from opencex_django.balance_hooks import OPENCEX_BALANCE_HOOKS
        g["OPENCEX_BALANCE_HOOKS"] = OPENCEX_BALANCE_HOOKS
    except Exception:
        g.setdefault("OPENCEX_BALANCE_HOOKS", {})
    g.setdefault("ZEROX_API_KEY", os.getenv("ZEROX_API_KEY", ""))
    g.setdefault("ZEROX_API_URL", os.getenv("ZEROX_API_URL", "https://api.0x.org"))
    g.setdefault("OPENCEX_SWAP_LIMITS", {
        "max_sell_usd": float(os.getenv("SWAP_MAX_SELL_USD", "50000")),
        "min_sell_wei": int(os.getenv("SWAP_MIN_SELL_WEI", "1000")),
        "allowed_chain_ids": [1, 56, 137, 42161, 8453],
        "token_whitelist_enabled": os.getenv("SWAP_TOKEN_WHITELIST", "1") == "1",
    })
    g.setdefault("OPENCEX_KYC_GATES", {
        "require_for_withdraw": os.getenv("KYC_REQUIRE_WITHDRAW", "1") == "1",
        "require_for_custodial_swap_above_usd": float(os.getenv("KYC_SWAP_THRESHOLD_USD", "1000")),
        "require_for_fiat": True,
    })
    g.setdefault("KYC_PRIMARY_PROVIDER", os.getenv("KYC_PRIMARY_PROVIDER", "zkme"))
    g.setdefault("ZKME_APP_ID", os.getenv("ZKME_APP_ID", ""))
    g.setdefault("ZKME_API_KEY", os.getenv("ZKME_API_KEY", ""))
