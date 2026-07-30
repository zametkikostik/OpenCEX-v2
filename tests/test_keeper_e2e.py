"""E2E-style tests for SwapKeeper + balance lock/unlock/credit. 12 tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def test_wei_to_decimal_eth():
    from opencex_django.balance_hooks import wei_to_decimal
    assert wei_to_decimal("1000000000000000000", "ETH") == Decimal("1")
    assert wei_to_decimal("500000", "USDT") == Decimal("0.5")


def test_wei_to_decimal_usdc():
    from opencex_django.balance_hooks import wei_to_decimal
    assert wei_to_decimal("1000000", "USDC") == Decimal("1")


class FakeBalance:
    def __init__(self, amount=Decimal("10"), amount_in_orders=Decimal("0")):
        self.amount = amount
        self.amount_in_orders = amount_in_orders


def _install_core_mocks(bal, currency="ETH"):
    currency_obj = SimpleNamespace(code=currency)
    balance_manager = MagicMock()
    balance_mod = MagicMock()
    currency_mod = MagicMock()
    currency_mod.Currency.get = MagicMock(return_value=currency_obj)
    qs = MagicMock()
    qs.first.return_value = bal
    qs.filter.return_value = qs
    balance_mod.Balance.objects = qs
    modules = {
        "core": MagicMock(),
        "core.balance_manager": balance_manager,
        "core.models": MagicMock(),
        "core.models.inouts": MagicMock(),
        "core.models.inouts.balance": balance_mod,
        "core.currency": currency_mod,
        "core.exceptions": MagicMock(),
        "core.exceptions.inouts": MagicMock(),
    }
    return modules, balance_manager


def test_lock_balance_calls_set_hold():
    bal = FakeBalance(amount=Decimal("5"))
    modules, bm = _install_core_mocks(bal)
    with patch.dict("sys.modules", modules):
        import importlib
        import opencex_django.balance_hooks as hooks
        importlib.reload(hooks)
        ok = hooks.lock_balance("42", "ETH", "1000000000000000000", 1)
        assert ok is True
        bm.BalanceManager.set_hold.assert_called_once()
        assert bm.BalanceManager.set_hold.call_args[0][2] == Decimal("1")


def test_unlock_balance_calls_free_hold():
    bal = FakeBalance(amount_in_orders=Decimal("1"))
    modules, bm = _install_core_mocks(bal)
    with patch.dict("sys.modules", modules):
        import importlib
        import opencex_django.balance_hooks as hooks
        importlib.reload(hooks)
        hooks.unlock_balance("42", "ETH", "1000000000000000000", 1)
        bm.BalanceManager.free_hold.assert_called_once()


def test_credit_balance_increases_buy():
    modules, bm = _install_core_mocks(FakeBalance(), "USDT")
    with patch.dict("sys.modules", modules):
        import importlib
        import opencex_django.balance_hooks as hooks
        importlib.reload(hooks)
        ok = hooks.credit_balance("42", "USDT", "1000000", 1)
        assert ok is True
        assert bm.BalanceManager.increase_amount.call_args[0][2] == Decimal("1")


def test_lock_insufficient_returns_false():
    modules, bm = _install_core_mocks(FakeBalance(amount=Decimal("0")))
    bm.BalanceManager.set_hold.side_effect = Exception("NotEnoughFunds")
    with patch.dict("sys.modules", modules):
        import importlib
        import opencex_django.balance_hooks as hooks
        importlib.reload(hooks)
        assert hooks.lock_balance("42", "ETH", "999000000000000000000", 1) is False


def _make_plan(**overrides):
    plan = {
        "chain_id": 1,
        "sell_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "buy_token": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "sell_amount": "1000000000000000000",
        "expected_buy_amount": "3000000000",
        "needs_allowance": False,
        "transaction": {
            "to": "0x0000000000001fF3684f28c67538d4D072C22734",
            "data": "0x1234",
            "value": "1000000000000000000",
            "gas": "250000",
        },
    }
    plan.update(overrides)
    return plan


@pytest.fixture
def keeper_mocks():
    w3 = MagicMock()
    w3.eth.get_transaction_count.return_value = 7
    w3.eth.estimate_gas.return_value = 21000
    w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}
    w3.to_wei.side_effect = lambda v, u: int(float(v) * 1e9) if u == "gwei" else int(v)
    tx_hash = MagicMock()
    tx_hash.hex = MagicMock(return_value="0xdeadbeef")
    w3.eth.send_raw_transaction.return_value = tx_hash
    w3.eth.get_transaction_receipt.return_value = {"status": 1, "blockNumber": 12345}
    w3.eth.gas_price = 1_000_000_000
    w3.to_checksum_address.side_effect = lambda x: x
    cfg = MagicMock(
        chain_id=1, private_key="0x" + "ab" * 32,
        address="0xKeeper0000000000000000000000000000000001",
        max_priority_gwei=2.0, max_fee_gwei=50.0,
        wait_timeout_sec=5, poll_interval_sec=0.01, private_rpc_url=None,
    )
    signed = MagicMock()
    signed.rawTransaction = b"\x01\x02"
    signed.raw_transaction = b"\x01\x02"
    with patch("opencex_swap_api.keeper.load_keeper_config", return_value=cfg), \
         patch("opencex_swap_api.keeper.Account") as Acc, \
         patch("opencex_swap_api.keeper.Web3") as W3cls, \
         patch("opencex_swap_api.keeper.time") as tmod:
        Acc.sign_transaction.return_value = signed
        Acc.from_key.return_value = MagicMock(address=cfg.address)
        W3cls.to_checksum_address.side_effect = lambda x: x
        tmod.time.side_effect = lambda: 0
        tmod.sleep = MagicMock()
        yield {"w3": w3}


def test_keeper_success_lock_credit_flow(keeper_mocks):
    from opencex_swap_api.keeper import SwapKeeper
    locked, credited, unlocked = [], [], []
    keeper = SwapKeeper(
        get_web3=lambda cid: keeper_mocks["w3"],
        lock_balance=lambda uid, sym, amt, chain: locked.append((uid, sym, amt)) or True,
        credit_balance=lambda uid, sym, amt, chain: credited.append((uid, sym, amt)) or True,
        unlock_balance=lambda uid, sym, amt, chain: unlocked.append((uid, sym, amt)),
    )
    result = keeper.execute(_make_plan(), "99", "ETH", "USDT")
    assert result.success is True
    assert result.tx_hash == "0xdeadbeef"
    assert locked == [("99", "ETH", "1000000000000000000")]
    assert credited == [("99", "USDT", "3000000000")]
    assert unlocked == []


def test_keeper_lock_fail_aborts(keeper_mocks):
    from opencex_swap_api.keeper import SwapKeeper
    keeper = SwapKeeper(
        get_web3=lambda cid: keeper_mocks["w3"],
        lock_balance=lambda *a, **k: False,
        credit_balance=lambda *a, **k: True,
    )
    result = keeper.execute(_make_plan(), "1", "ETH", "USDT")
    assert result.success is False
    assert result.error == "insufficient_balance_or_lock_failed"
    keeper_mocks["w3"].eth.send_raw_transaction.assert_not_called()


def test_keeper_tx_revert_unlocks(keeper_mocks):
    from opencex_swap_api.keeper import SwapKeeper
    keeper_mocks["w3"].eth.get_transaction_receipt.return_value = {"status": 0, "blockNumber": 1}
    unlocked = []
    keeper = SwapKeeper(
        get_web3=lambda cid: keeper_mocks["w3"],
        lock_balance=lambda *a, **k: True,
        credit_balance=lambda *a, **k: True,
        unlock_balance=lambda *a, **k: unlocked.append(a),
    )
    result = keeper.execute(_make_plan(), "5", "ETH", "USDT")
    assert result.success is False
    assert result.error == "tx_reverted"
    assert len(unlocked) == 1


def test_keeper_missing_config():
    from opencex_swap_api.keeper import SwapKeeper
    with patch("opencex_swap_api.keeper.load_keeper_config", return_value=None):
        result = SwapKeeper(lock_balance=lambda *a, **k: True).execute(_make_plan(), "1", "ETH", "USDT")
        assert result.success is False
        assert result.error == "keeper_not_configured"


def test_keeper_missing_calldata(keeper_mocks):
    from opencex_swap_api.keeper import SwapKeeper
    result = SwapKeeper(
        get_web3=lambda cid: keeper_mocks["w3"],
        lock_balance=lambda *a, **k: True,
    ).execute(_make_plan(transaction={}), "1", "ETH", "USDT")
    assert result.success is False
    assert result.error == "missing_transaction_calldata"


def test_opencex_balance_hooks_export():
    from opencex_django.balance_hooks import OPENCEX_BALANCE_HOOKS
    assert callable(OPENCEX_BALANCE_HOOKS["lock"])
    assert callable(OPENCEX_BALANCE_HOOKS["credit"])
    assert callable(OPENCEX_BALANCE_HOOKS["unlock"])
