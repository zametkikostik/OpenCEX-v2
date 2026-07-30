from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional
from .protocol_fee import apply_fee_to_amount, load_fee_config

@dataclass
class FeeRow:
    execution_id: Any; sell_amount_wei: str; fee_wei: str; net_wei: str; chain_id: int; status: str

def reconcile_from_plans(plans: List[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = load_fee_config(); rows = []; total = Decimal(0)
    for p in plans:
        if p.get("status") not in ("success", "SUCCESS", True): continue
        net, fee = apply_fee_to_amount(str(p["sell_amount"]), cfg.fee_bps)
        total += Decimal(fee)
        rows.append(FeeRow(p.get("id"), str(p["sell_amount"]), fee, net, int(p.get("chain_id", 1)), str(p.get("status"))))
    return {"fee_bps": cfg.fee_bps, "recipient": cfg.recipient, "fills": len(rows),
            "total_fee_wei": str(int(total)), "rows": [r.__dict__ for r in rows]}

def django_reconcile_recent(limit=100):
    try:
        from opencex_django.models import SwapExecution
    except Exception as e:
        return {"error": str(e)}
    qs = SwapExecution.objects.filter(status="success").order_by("-id")[:limit]
    return reconcile_from_plans([{"id": x.id, "sell_amount": x.sell_amount, "chain_id": x.chain_id, "status": x.status} for x in qs])
