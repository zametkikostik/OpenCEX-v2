"""Celery tasks: execute_swap_task, refresh_kyc_task, enqueue_swap."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("opencex_django.tasks")

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(fn):
            fn.delay = lambda *a, **k: fn(*a, **k)
            fn.apply_async = lambda *a, **k: fn(*a, **k)
            return fn
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def _get_balance_hooks():
    try:
        from django.conf import settings
        hooks = getattr(settings, "OPENCEX_BALANCE_HOOKS", None) or {}
        return hooks.get("lock"), hooks.get("credit"), hooks.get("unlock")
    except Exception:
        return None, None, None


@shared_task(bind=True, name="opencex.execute_swap", max_retries=2, default_retry_delay=15, acks_late=True)
def execute_swap_task(self, execution_id: int, user_id: str, sell_symbol: str, buy_symbol: str) -> Dict[str, Any]:
    from django.db import transaction
    from opencex_django.models import SwapExecution
    from opencex_swap_api.keeper import SwapKeeper

    try:
        execution = SwapExecution.objects.get(pk=execution_id)
    except SwapExecution.DoesNotExist:
        return {"success": False, "error": "execution_not_found"}

    if execution.status not in (SwapExecution.Status.QUEUED, SwapExecution.Status.FAILED):
        return {"success": False, "error": f"invalid_status_{execution.status}"}

    execution.status = SwapExecution.Status.BROADCASTING
    execution.celery_task_id = getattr(self.request, "id", None)
    execution.save(update_fields=["status", "celery_task_id", "updated_at"])

    lock_fn, credit_fn, unlock_fn = _get_balance_hooks()

    def _noop_lock(*a, **k):
        return True

    def _noop_credit(*a, **k):
        return True

    def _noop_unlock(*a, **k):
        return None

    keeper = SwapKeeper(
        lock_balance=lock_fn or _noop_lock,
        credit_balance=credit_fn or _noop_credit,
        unlock_balance=unlock_fn or _noop_unlock,
    )

    plan = execution.plan or {}
    plan.setdefault("chain_id", execution.chain_id)
    plan.setdefault("sell_amount", execution.sell_amount)
    plan.setdefault("sell_token", execution.sell_token)
    plan.setdefault("buy_token", execution.buy_token)
    plan.setdefault("expected_buy_amount", execution.expected_buy_amount)

    try:
        result = keeper.execute(plan=plan, user_id=str(user_id), sell_symbol=sell_symbol, buy_symbol=buy_symbol)
    except Exception as exc:
        log.exception("execute_swap_task failed")
        execution.status = SwapExecution.Status.FAILED
        execution.error = str(exc)
        execution.save(update_fields=["status", "error", "updated_at"])
        raise self.retry(exc=exc)

    with transaction.atomic():
        execution.refresh_from_db()
        if result.success:
            execution.status = SwapExecution.Status.SUCCESS
            execution.tx_hash = result.tx_hash
            execution.block_number = result.block_number
            execution.actual_buy_amount = result.buy_amount
            execution.error = None
        else:
            execution.status = (
                SwapExecution.Status.REVERTED if result.error == "tx_reverted" else SwapExecution.Status.FAILED
            )
            execution.tx_hash = result.tx_hash
            execution.error = result.error
        execution.save()

    return {"success": result.success, "execution_id": execution_id, "tx_hash": result.tx_hash, "error": result.error}


@shared_task(name="opencex.refresh_kyc")
def refresh_kyc_task(user_id: str, provider: Optional[str] = None) -> Dict[str, Any]:
    from opencex_django.models import UserKYC
    from opencex_kyc.models import KYCProvider
    from opencex_kyc.service import KYCService
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    svc = KYCService()
    p = KYCProvider(provider) if provider else None
    result_rec = svc.refresh_from_provider(str(user_id), provider=p)
    kyc, _ = UserKYC.objects.get_or_create(user=user)
    kyc.apply_result(
        status=result_rec.status.value,
        provider=result_rec.provider.value if result_rec.provider else None,
        level=result_rec.level.value if result_rec.level else None,
        claims=result_rec.claims,
        credential_id=result_rec.credential_id,
        proof_hash=result_rec.proof_hash,
    )
    return {"success": True, "status": kyc.status, "is_verified": kyc.is_verified}


def enqueue_swap(user, plan: Dict[str, Any], sell_symbol: str, buy_symbol: str, client_order_id: Optional[str] = None):
    from opencex_django.models import SwapExecution

    execution = SwapExecution.objects.create(
        user=user,
        client_order_id=client_order_id,
        chain_id=int(plan.get("chain_id", 1)),
        sell_symbol=sell_symbol,
        buy_symbol=buy_symbol,
        sell_token=plan.get("sell_token", ""),
        buy_token=plan.get("buy_token", ""),
        sell_amount=str(plan.get("sell_amount", "0")),
        expected_buy_amount=plan.get("expected_buy_amount") or plan.get("buy_amount"),
        status=SwapExecution.Status.QUEUED,
        plan=plan,
    )
    async_result = execute_swap_task.delay(
        execution_id=execution.id,
        user_id=str(user.id),
        sell_symbol=sell_symbol,
        buy_symbol=buy_symbol,
    )
    execution.celery_task_id = async_result.id
    execution.save(update_fields=["celery_task_id", "updated_at"])
    return execution
