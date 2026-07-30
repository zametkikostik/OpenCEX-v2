from __future__ import annotations
import logging, os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .orders import NCOrder, verify_order_signature
log = logging.getLogger("opencex_settlement")

FILL_ORDER_ABI = [{"name": "fillOrder", "type": "function", "stateMutability": "nonpayable",
    "inputs": [{"name": "order", "type": "tuple", "components": [
        {"name": "maker", "type": "address"}, {"name": "sellToken", "type": "address"},
        {"name": "buyToken", "type": "address"}, {"name": "sellAmount", "type": "uint256"},
        {"name": "buyAmount", "type": "uint256"}, {"name": "nonce", "type": "uint256"},
        {"name": "expiry", "type": "uint256"}, {"name": "salt", "type": "uint256"}]},
        {"name": "signature", "type": "bytes"}],
    "outputs": [{"name": "filled", "type": "uint256"}]}]

@dataclass
class SettlementPlan:
    mode: str; chain_id: int; order: Dict[str, Any]; signature: str
    tx: Optional[Dict[str, Any]] = None; verifying_contract: Optional[str] = None
    notes: List[str] = field(default_factory=list)

class SettlementService:
    def settlement_contract(self, chain_id):
        return os.getenv(f"SETTLEMENT_CONTRACT_{chain_id}") or os.getenv("SETTLEMENT_CONTRACT")
    def validate_signed_order(self, order, signature, verifying_contract=None):
        if order.is_expired(): raise ValueError("order_expired")
        vc = verifying_contract or self.settlement_contract(order.chain_id) or "0x0000000000000000000000000000000000000000"
        if not verify_order_signature(order, signature, vc): raise ValueError("invalid_signature")
    def build_plan(self, order, signature, verifying_contract=None):
        vc = verifying_contract or self.settlement_contract(order.chain_id)
        self.validate_signed_order(order, signature, vc)
        if vc and vc != "0x0000000000000000000000000000000000000000":
            return SettlementPlan("contract", order.chain_id, order.__dict__, signature,
                tx=self._encode_fill(order, signature, vc), verifying_contract=vc,
                notes=["fillOrder on settlement; maker must approve sellToken"])
        return SettlementPlan("self", order.chain_id, order.__dict__, signature, verifying_contract=vc,
            notes=["No SETTLEMENT_CONTRACT — use NC swap / 0x"])
    def _encode_fill(self, order, signature, contract):
        from web3 import Web3
        w3 = Web3(); c = w3.eth.contract(address=Web3.to_checksum_address(contract), abi=FILL_ORDER_ABI)
        sig = signature if signature.startswith("0x") else "0x" + signature
        ot = (Web3.to_checksum_address(order.maker), Web3.to_checksum_address(order.sell_token),
              Web3.to_checksum_address(order.buy_token), int(order.sell_amount), int(order.buy_amount),
              int(order.nonce), int(order.expiry), int(order.salt) if str(order.salt).isdigit() else 0)
        data = c.encode_abi("fillOrder", args=[ot, sig])
        return {"to": contract, "data": data, "value": 0, "chainId": order.chain_id}
