from __future__ import annotations
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
ENTRYPOINT_V06 = {1: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789", 56: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789",
    137: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789", 42161: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789",
    8453: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789", 11155111: "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"}

@dataclass
class UserOperation:
    sender: str; nonce: str; initCode: str = "0x"; callData: str = "0x"
    callGasLimit: str = "0x0"; verificationGasLimit: str = "0x0"; preVerificationGas: str = "0x0"
    maxFeePerGas: str = "0x0"; maxPriorityFeePerGas: str = "0x0"; paymasterAndData: str = "0x"; signature: str = "0x"
    def to_rpc(self): return asdict(self)

@dataclass
class UserOpBuilder:
    chain_id: int; entry_point: Optional[str] = None; account_address: str = ""
    def __post_init__(self):
        if not self.entry_point:
            self.entry_point = os.getenv(f"ENTRYPOINT_{self.chain_id}") or ENTRYPOINT_V06.get(self.chain_id) or ENTRYPOINT_V06[1]
    def build_execute(self, target, data, value=0, nonce=0, encode_simple_account=True):
        call_data = self._encode_simple_execute(target, value, data) if encode_simple_account and target else data
        if not str(call_data).startswith("0x"): call_data = "0x" + call_data
        return UserOperation(sender=self.account_address, nonce=hex(nonce), callData=call_data,
            callGasLimit=hex(int(os.getenv("AA_CALL_GAS", "300000"))),
            verificationGasLimit=hex(int(os.getenv("AA_VERIF_GAS", "100000"))),
            preVerificationGas=hex(int(os.getenv("AA_PREV_GAS", "50000"))),
            maxFeePerGas=hex(int(os.getenv("AA_MAX_FEE_WEI", "30000000000"))),
            maxPriorityFeePerGas=hex(int(os.getenv("AA_PRIORITY_WEI", "1000000000"))))
    def build_from_settlement_tx(self, tx, nonce=0):
        return self.build_execute(tx["to"], tx.get("data") or "0x", int(tx.get("value") or 0), nonce)
    @staticmethod
    def _encode_simple_execute(target, value, data):
        try:
            from eth_abi import encode
            from eth_utils import function_signature_to_4byte_selector
            sel = function_signature_to_4byte_selector("execute(address,uint256,bytes)")
            payload = data[2:] if data.startswith("0x") else data
            return "0x" + sel.hex() + encode(["address", "uint256", "bytes"], [target, value, bytes.fromhex(payload or "")]).hex()
        except Exception:
            return data
