"""Hybrid Wallet service — custodial / non-custodial / hybrid."""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .eip712 import order_typed_data, recover_signer
from .models import SignedOrder, WalletMode, WalletSession

log = logging.getLogger("opencex_wallet")

DEFAULT_VERIFYING = os.getenv(
    "OPENCEX_SETTLEMENT_ADDRESS",
    "0x0000000000001fF3684f28c67538d4D072C22734",
)


class HybridWalletService:
    def __init__(self, verifying_contract: Optional[str] = None):
        self.verifying_contract = verifying_contract or DEFAULT_VERIFYING
        self._sessions: Dict[str, WalletSession] = {}
        self._orders: Dict[str, SignedOrder] = {}
        self._nonces: Dict[str, int] = {}

    def create_session(self, user_id, mode, address=None, chain_id=1):
        if mode in (WalletMode.NON_CUSTODIAL, WalletMode.HYBRID) and not address:
            raise ValueError("address required for non-custodial / hybrid mode")
        if address and not (address.startswith("0x") and len(address) == 42):
            raise ValueError("invalid address")
        session = WalletSession(
            user_id=str(user_id),
            mode=mode,
            address=address,
            chain_id=chain_id,
            session_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id):
        return self._sessions.get(session_id)

    def build_order_typed_data(
        self, chain_id, trader, sell_token, buy_token, sell_amount, min_buy_amount, expiry_sec=600
    ):
        key = f"{chain_id}:{trader.lower()}"
        nonce = self._nonces.get(key, 0)
        expiry = int(time.time()) + expiry_sec
        return order_typed_data(
            chain_id=chain_id,
            verifying_contract=self.verifying_contract,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=sell_amount,
            min_buy_amount=min_buy_amount,
            nonce=nonce,
            expiry=expiry,
            trader=trader,
        )

    def submit_signed_order(self, user_id, typed_data, signature, mode=WalletMode.NON_CUSTODIAL):
        msg = typed_data.get("message") or {}
        try:
            signer = recover_signer(typed_data, signature)
        except Exception as exc:
            raise ValueError(f"invalid signature: {exc}") from exc
        trader = msg.get("trader", "")
        if signer.lower() != trader.lower():
            raise ValueError(f"signer {signer} != trader {trader}")
        order_id = str(uuid.uuid4())
        order = SignedOrder(
            order_id=order_id,
            user_id=str(user_id),
            chain_id=int(typed_data["domain"]["chainId"]),
            sell_token=msg["sellToken"],
            buy_token=msg["buyToken"],
            sell_amount=str(msg["sellAmount"]),
            min_buy_amount=str(msg["minBuyAmount"]),
            nonce=int(msg["nonce"]),
            expiry=int(msg["expiry"]),
            signature=signature,
            signer=signer,
            mode=mode,
            status="open",
            raw={"typed_data": typed_data},
        )
        self._orders[order_id] = order
        key = f"{order.chain_id}:{trader.lower()}"
        self._nonces[key] = order.nonce + 1
        return order

    def get_order(self, order_id):
        return self._orders.get(order_id)

    def prepare_zerox_for_user(self, chain_id, sell_token, buy_token, sell_amount, taker):
        from opencex_liquidity import ZeroXClient

        quote = ZeroXClient().get_quote(
            chain_id=chain_id,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=sell_amount,
            taker=taker,
        )
        return {
            "mode": WalletMode.NON_CUSTODIAL.value,
            "needs_allowance": quote.needs_allowance,
            "allowance_spender": quote.allowance_spender,
            "transaction": quote.to_tx_dict(),
            "buy_amount": quote.buy_amount,
            "sell_amount": quote.sell_amount,
            "price": quote.price,
            "message": "User must sign transaction in their wallet",
        }
