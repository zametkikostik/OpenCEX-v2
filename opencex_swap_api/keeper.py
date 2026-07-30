"""
Custodial swap keeper pipeline for /api/v1/swap/execute/

Flow: lock → allowance → sign → broadcast (optional private RPC) → credit
MEV: set PRIVATE_RPC_URL to Flashbots Protect / MEV Blocker endpoint.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from eth_account import Account
from web3 import Web3

log = logging.getLogger("opencex_swap.keeper")


@dataclass
class KeeperConfig:
    chain_id: int
    private_key: str
    address: str
    max_priority_gwei: float = 2.0
    max_fee_gwei: float = 50.0
    wait_timeout_sec: int = 120
    poll_interval_sec: float = 2.0
    private_rpc_url: Optional[str] = None


@dataclass
class ExecutionResult:
    success: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    buy_amount: Optional[str] = None
    error: Optional[str] = None
    receipt: Dict[str, Any] = field(default_factory=dict)


def load_keeper_config(chain_id: int) -> Optional[KeeperConfig]:
    key_map = {
        1: "ETH_KEEPER_PRIVATE_KEY",
        56: "BNB_KEEPER_PRIVATE_KEY",
        137: "MATIC_KEEPER_PRIVATE_KEY",
        42161: "ARB_KEEPER_PRIVATE_KEY",
        8453: "BASE_KEEPER_PRIVATE_KEY",
    }
    pk = os.getenv(key_map.get(chain_id, ""), "")
    if not pk:
        return None
    if not pk.startswith("0x"):
        pk = "0x" + pk
    acct = Account.from_key(pk)
    private_rpc = os.getenv(f"PRIVATE_RPC_{chain_id}") or os.getenv("PRIVATE_RPC_URL")
    return KeeperConfig(
        chain_id=chain_id,
        private_key=pk,
        address=acct.address,
        private_rpc_url=private_rpc,
    )


class SwapKeeper:
    def __init__(self, get_web3=None, lock_balance=None, credit_balance=None, unlock_balance=None):
        self._get_web3 = get_web3
        self.lock_balance = lock_balance
        self.credit_balance = credit_balance
        self.unlock_balance = unlock_balance

    def _web3(self, chain_id, cfg):
        if cfg.private_rpc_url:
            log.info("Using private RPC for chain %s (MEV protection)", chain_id)
            return Web3(Web3.HTTPProvider(cfg.private_rpc_url, request_kwargs={"timeout": 30}))
        if self._get_web3:
            return self._get_web3(chain_id)
        from opencex_rpc import get_web3
        return get_web3(chain_id)

    def execute(self, plan, user_id, sell_symbol, buy_symbol) -> ExecutionResult:
        chain_id = int(plan["chain_id"])
        cfg = load_keeper_config(chain_id)
        if not cfg:
            return ExecutionResult(success=False, error="keeper_not_configured")

        sell_amount = plan["sell_amount"]
        tx_data = plan.get("transaction") or {}
        if not tx_data.get("to") or not tx_data.get("data"):
            return ExecutionResult(success=False, error="missing_transaction_calldata")

        if self.lock_balance:
            if not self.lock_balance(user_id, sell_symbol, sell_amount, chain_id):
                return ExecutionResult(success=False, error="insufficient_balance_or_lock_failed")

        w3 = self._web3(chain_id, cfg)
        try:
            if plan.get("needs_allowance") and plan.get("allowance_spender"):
                self._ensure_allowance(
                    w3, cfg, token=plan["sell_token"],
                    spender=plan["allowance_spender"], amount=int(sell_amount),
                )

            nonce = w3.eth.get_transaction_count(cfg.address)
            tx = {
                "to": Web3.to_checksum_address(tx_data["to"]),
                "data": tx_data["data"],
                "value": int(tx_data.get("value") or 0),
                "nonce": nonce,
                "chainId": chain_id,
                "from": cfg.address,
            }
            tx["gas"] = int(tx_data["gas"]) if tx_data.get("gas") else w3.eth.estimate_gas(tx)
            try:
                base = (w3.eth.get_block("latest").get("baseFeePerGas") or 0)
                priority = w3.to_wei(cfg.max_priority_gwei, "gwei")
                tx["maxPriorityFeePerGas"] = priority
                tx["maxFeePerGas"] = min(base * 2 + priority, w3.to_wei(cfg.max_fee_gwei, "gwei"))
            except Exception:
                tx["gasPrice"] = w3.eth.gas_price

            signed = Account.sign_transaction(tx, cfg.private_key)
            raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
            tx_hash = w3.eth.send_raw_transaction(raw)
            tx_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
            log.info("Swap tx sent chain=%s hash=%s", chain_id, tx_hex)

            receipt = self._wait_receipt(w3, tx_hash, cfg)
            if receipt is None:
                if self.unlock_balance:
                    self.unlock_balance(user_id, sell_symbol, sell_amount, chain_id)
                return ExecutionResult(success=False, tx_hash=tx_hex, error="timeout_waiting_receipt")

            if int(receipt.get("status", 0)) != 1:
                if self.unlock_balance:
                    self.unlock_balance(user_id, sell_symbol, sell_amount, chain_id)
                return ExecutionResult(success=False, tx_hash=tx_hex, error="tx_reverted")

            buy_amount = plan.get("expected_buy_amount") or plan.get("buy_amount")
            if self.credit_balance and buy_amount:
                self.credit_balance(user_id, buy_symbol, buy_amount, chain_id)

            return ExecutionResult(
                success=True, tx_hash=tx_hex,
                block_number=receipt.get("blockNumber"), buy_amount=buy_amount,
            )
        except Exception as exc:
            log.exception("Keeper execute failed")
            if self.unlock_balance:
                try:
                    self.unlock_balance(user_id, sell_symbol, sell_amount, chain_id)
                except Exception:
                    pass
            return ExecutionResult(success=False, error=str(exc))

    def _ensure_allowance(self, w3, cfg, token, spender, amount):
        native = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        if token.lower() == native.lower():
            return
        abi = [
            {"name": "allowance", "type": "function", "stateMutability": "view",
             "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"name": "approve", "type": "function", "stateMutability": "nonpayable",
             "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
             "outputs": [{"name": "", "type": "bool"}]},
        ]
        c = w3.eth.contract(address=Web3.to_checksum_address(token), abi=abi)
        if c.functions.allowance(cfg.address, Web3.to_checksum_address(spender)).call() >= amount:
            return
        nonce = w3.eth.get_transaction_count(cfg.address)
        tx = c.functions.approve(Web3.to_checksum_address(spender), 2**256 - 1).build_transaction({
            "from": cfg.address, "nonce": nonce, "chainId": cfg.chain_id, "gas": 80000,
        })
        try:
            tx["maxFeePerGas"] = w3.to_wei(cfg.max_fee_gwei, "gwei")
            tx["maxPriorityFeePerGas"] = w3.to_wei(cfg.max_priority_gwei, "gwei")
        except Exception:
            tx["gasPrice"] = w3.eth.gas_price
        signed = Account.sign_transaction(tx, cfg.private_key)
        raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
        h = w3.eth.send_raw_transaction(raw)
        w3.eth.wait_for_transaction_receipt(h, timeout=cfg.wait_timeout_sec)

    def _wait_receipt(self, w3, tx_hash, cfg):
        deadline = time.time() + cfg.wait_timeout_sec
        while time.time() < deadline:
            try:
                r = w3.eth.get_transaction_receipt(tx_hash)
                if r is not None:
                    return r
            except Exception:
                pass
            time.sleep(cfg.poll_interval_sec)
        return None
