"""ERC-4337 Paymaster: API sponsor or local verifying paymasterAndData."""
from __future__ import annotations
import json, logging, os, time, urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .userop import UserOperation
log = logging.getLogger("opencex_aa.paymaster")

@dataclass
class PaymasterResult:
    paymaster_and_data: str; policy: str; sponsored: bool; detail: str = ""

class PaymasterClient:
    def __init__(self, chain_id: int):
        self.chain_id = chain_id
        self.url = os.getenv(f"PAYMASTER_URL_{chain_id}") or os.getenv("PAYMASTER_URL") or ""
        self.address = os.getenv(f"PAYMASTER_ADDRESS_{chain_id}") or os.getenv("PAYMASTER_ADDRESS") or ""
        self.policy = os.getenv("PAYMASTER_POLICY", "sponsor_settlement")
        self.signer_key = os.getenv("PAYMASTER_SIGNER_KEY") or ""
    def should_sponsor(self, context=None) -> bool:
        if self.policy == "none": return False
        if self.policy == "sponsor_all": return True
        if self.policy == "sponsor_settlement":
            ctx = context or {}
            return bool(ctx.get("is_settlement") or ctx.get("kind") == "settlement")
        return False
    def sponsor(self, user_op, entry_point, context=None) -> PaymasterResult:
        if not self.should_sponsor(context):
            return PaymasterResult("0x", self.policy, False, "policy_skip")
        if self.url: return self._sponsor_api(user_op, entry_point, context)
        if self.address and self.signer_key: return self._sponsor_verifying(user_op)
        if self.address:
            return PaymasterResult("0x" + self.address.lower().replace("0x", ""), self.policy, True, "address_only")
        return PaymasterResult("0x", self.policy, False, "not_configured")
    def _sponsor_api(self, user_op, entry_point, context):
        payload = {"jsonrpc": "2.0", "id": 1, "method": "pm_sponsorUserOperation",
                   "params": [user_op.to_rpc(), entry_point, context or {}]}
        try:
            req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
            if "error" in body: return PaymasterResult("0x", self.policy, False, str(body["error"]))
            result = body.get("result") or {}
            pad = result if isinstance(result, str) else (result.get("paymasterAndData") or "0x")
            return PaymasterResult(pad, self.policy, pad != "0x", "api")
        except Exception as e:
            return PaymasterResult("0x", self.policy, False, type(e).__name__)
    def _sponsor_verifying(self, user_op):
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
        except ImportError:
            return PaymasterResult("0x", self.policy, False, "no_eth_account")
        valid_until = int(time.time()) + int(os.getenv("PAYMASTER_VALID_SEC", "3600"))
        pre = self.address.lower().replace("0x", "").zfill(40) + f"{valid_until:012x}" + f"{0:012x}"
        msg = f"opencex-pm:{user_op.sender}:{user_op.nonce}:{valid_until}:0"
        pk = self.signer_key if self.signer_key.startswith("0x") else "0x" + self.signer_key
        sig = Account.sign_message(encode_defunct(text=msg), private_key=pk).signature.hex().replace("0x", "")
        return PaymasterResult("0x" + pre + sig, self.policy, True, "verifying_local")

def attach_paymaster(user_op, chain_id, entry_point, context=None):
    r = PaymasterClient(chain_id).sponsor(user_op, entry_point, context)
    if r.sponsored and r.paymaster_and_data not in ("", "0x"):
        user_op.paymasterAndData = r.paymaster_and_data
        _metric(chain_id, "sponsored")
    else:
        _metric(chain_id, "skipped")
    return user_op

def _metric(chain_id, result):
    try:
        from prometheus_client import Counter
        Counter("opencex_aa_paymaster_total", "Paymaster", ["chain_id", "result"]).labels(
            chain_id=str(chain_id), result=result).inc()
    except Exception:
        pass
