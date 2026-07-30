from __future__ import annotations
import json, logging, os, urllib.request
from typing import Any, Dict, Optional
from .userop import ENTRYPOINT_V06, UserOperation
log = logging.getLogger("opencex_aa.bundler")

class BundlerClient:
    def __init__(self, chain_id, url=None):
        self.chain_id = chain_id
        self.url = url or os.getenv(f"BUNDLER_URL_{chain_id}") or os.getenv("BUNDLER_URL") or ""
        self.entry_point = os.getenv(f"ENTRYPOINT_{chain_id}") or ENTRYPOINT_V06.get(chain_id) or ENTRYPOINT_V06[1]
    def _rpc(self, method, params):
        if not self.url: raise RuntimeError("BUNDLER_URL not configured")
        req = urllib.request.Request(self.url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        if "error" in data: raise RuntimeError(data["error"])
        return data.get("result")
    def estimate_user_operation_gas(self, user_op):
        return self._rpc("eth_estimateUserOperationGas", [user_op.to_rpc(), self.entry_point])
    def send_user_operation(self, user_op):
        return self._rpc("eth_sendUserOperation", [user_op.to_rpc(), self.entry_point])
    def get_user_operation_receipt(self, user_op_hash):
        return self._rpc("eth_getUserOperationReceipt", [user_op_hash])
