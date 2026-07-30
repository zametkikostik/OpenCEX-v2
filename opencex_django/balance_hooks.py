"""OPENCEX_BALANCE_HOOKS bound to OpenCEX BalanceManager."""

from __future__ import annotations

import logging
from decimal import Decimal, getcontext
from typing import Optional

log = logging.getLogger("opencex_django.balance_hooks")
getcontext().prec = 50

TOKEN_DECIMALS = {
    "ETH": 18, "BNB": 18, "MATIC": 18, "WETH": 18, "WBNB": 18, "WMATIC": 18,
    "USDT": 6, "USDC": 6, "DAI": 18, "BUSD": 18,
}


def wei_to_decimal(amount_wei, symbol: str) -> Decimal:
    decimals = TOKEN_DECIMALS.get(str(symbol).upper(), 18)
    return Decimal(str(amount_wei)) / (Decimal(10) ** decimals)


def _resolve_currency(symbol: str):
    from core.currency import Currency
    return Currency.get(str(symbol).upper())


def lock_balance(user_id, sell_symbol, sell_amount_wei, chain_id=1) -> bool:
    try:
        from core.balance_manager import BalanceManager
        from core.models.inouts.balance import Balance
    except ImportError as exc:
        log.error("BalanceManager unavailable: %s", exc)
        return False
    try:
        currency = _resolve_currency(sell_symbol)
        amount = wei_to_decimal(sell_amount_wei, sell_symbol)
        uid = int(user_id)
        bal = Balance.objects.filter(user_id=uid, currency=currency).first()
        current = bal.amount_in_orders if bal else Decimal(0)
        BalanceManager.set_hold(uid, currency, amount, current + amount)
        log.info("Locked %s %s user=%s", amount, sell_symbol, user_id)
        return True
    except Exception as exc:
        log.warning("lock_balance failed: %s", exc)
        return False


def unlock_balance(user_id, sell_symbol, sell_amount_wei, chain_id=1) -> None:
    try:
        from core.balance_manager import BalanceManager
        from core.models.inouts.balance import Balance
    except ImportError:
        return
    try:
        currency = _resolve_currency(sell_symbol)
        amount = wei_to_decimal(sell_amount_wei, sell_symbol)
        uid = int(user_id)
        bal = Balance.objects.filter(user_id=uid, currency=currency).first()
        current = bal.amount_in_orders if bal else Decimal(0)
        BalanceManager.free_hold(uid, currency, amount, max(current - amount, Decimal(0)))
        log.info("Unlocked %s %s user=%s", amount, sell_symbol, user_id)
    except Exception as exc:
        log.exception("unlock_balance failed: %s", exc)


def credit_balance(user_id, buy_symbol, buy_amount_wei, chain_id=1,
                   sell_symbol: Optional[str] = None, sell_amount_wei: Optional[str] = None) -> bool:
    try:
        from core.balance_manager import BalanceManager
        from core.models.inouts.balance import Balance
    except ImportError:
        return False
    try:
        uid = int(user_id)
        buy_currency = _resolve_currency(buy_symbol)
        buy_amount = wei_to_decimal(buy_amount_wei, buy_symbol)
        if sell_symbol and sell_amount_wei:
            sell_currency = _resolve_currency(sell_symbol)
            sell_amount = wei_to_decimal(sell_amount_wei, sell_symbol)
            bal = Balance.objects.filter(user_id=uid, currency=sell_currency).first()
            current = bal.amount_in_orders if bal else Decimal(0)
            BalanceManager.spend_hold(uid, sell_currency, max(current - sell_amount, Decimal(0)))
        BalanceManager.increase_amount(uid, buy_currency, buy_amount)
        log.info("Credited %s %s user=%s", buy_amount, buy_symbol, user_id)
        return True
    except Exception as exc:
        log.exception("credit_balance failed: %s", exc)
        return False


def credit_balance_keeper(user_id, buy_symbol, buy_amount_wei, chain_id=1) -> bool:
    return credit_balance(user_id, buy_symbol, buy_amount_wei, chain_id)


OPENCEX_BALANCE_HOOKS = {
    "lock": lock_balance,
    "credit": credit_balance_keeper,
    "unlock": unlock_balance,
}
