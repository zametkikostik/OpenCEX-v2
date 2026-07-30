from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from opencex_django.permissions import kyc_required_for_swap_amount, user_kyc_verified

def check_swap_kyc(user, plan: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    usd = plan.get("sell_amount_usd") or plan.get("estimated_sell_usd")
    try:
        usd_f = float(usd) if usd is not None else None
    except (TypeError, ValueError):
        usd_f = None
    if not kyc_required_for_swap_amount(usd_f):
        return True, None
    if user_kyc_verified(user):
        return True, None
    return False, "kyc_required_for_swap_amount"
