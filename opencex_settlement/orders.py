from __future__ import annotations
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data

@dataclass
class NCOrder:
    maker: str; sell_token: str; buy_token: str
    sell_amount: str; buy_amount: str; chain_id: int; nonce: int; expiry: int; salt: str = "0"
    def to_message(self):
        return {"maker": self.maker, "sellToken": self.sell_token, "buyToken": self.buy_token,
                "sellAmount": int(self.sell_amount), "buyAmount": int(self.buy_amount),
                "nonce": int(self.nonce), "expiry": int(self.expiry),
                "salt": int(self.salt) if str(self.salt).isdigit() else 0}
    def is_expired(self, now=None): return int(now or time.time()) >= int(self.expiry)

ORDER_TYPES = {"Order": [
    {"name": "maker", "type": "address"}, {"name": "sellToken", "type": "address"},
    {"name": "buyToken", "type": "address"}, {"name": "sellAmount", "type": "uint256"},
    {"name": "buyAmount", "type": "uint256"}, {"name": "nonce", "type": "uint256"},
    {"name": "expiry", "type": "uint256"}, {"name": "salt", "type": "uint256"},
]}

def eip712_domain(chain_id, verifying_contract="0x0000000000000000000000000000000000000000"):
    return {"name": "OpenCEX", "version": "1", "chainId": chain_id, "verifyingContract": verifying_contract}

def _full(order, verifying_contract):
    return {"types": {"EIP712Domain": [
        {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"},
    ], **ORDER_TYPES}, "primaryType": "Order",
        "domain": eip712_domain(order.chain_id, verifying_contract), "message": order.to_message()}

def hash_order(order, verifying_contract="0x0000000000000000000000000000000000000000"):
    signable = encode_typed_data(full_message=_full(order, verifying_contract))
    return signable.body.hex() if hasattr(signable.body, "hex") else str(signable)

def verify_order_signature(order, signature, verifying_contract="0x0000000000000000000000000000000000000000") -> bool:
    sig = signature if signature.startswith("0x") else "0x" + signature
    try:
        recovered = Account.recover_typed_data(_full(order, verifying_contract), signature=sig)
        return recovered.lower() == order.maker.lower()
    except Exception:
        try:
            signable = encode_typed_data(full_message=_full(order, verifying_contract))
            recovered = Account.recover_message(signable, signature=sig)
            return recovered.lower() == order.maker.lower()
        except Exception:
            return False

def order_to_dict(order): return asdict(order)
