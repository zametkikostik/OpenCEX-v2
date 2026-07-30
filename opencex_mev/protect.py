from __future__ import annotations
import json, logging, os, urllib.request
from dataclasses import dataclass
from typing import Optional
log = logging.getLogger("opencex_mev")

@dataclass
class MEVConfig:
    enabled: bool = True
    private_rpc: Optional[str] = None
    flashbots_rpc: Optional[str] = None
    max_priority_gwei: float = 2.0

def load_mev_config(chain_id: int) -> MEVConfig:
    return MEVConfig(
        enabled=os.getenv("MEV_PROTECT", "1") == "1",
        private_rpc=os.getenv(f"PRIVATE_RPC_{chain_id}") or os.getenv("PRIVATE_RPC_URL") or None,
        flashbots_rpc=os.getenv("FLASHBOTS_RPC") or os.getenv("FLASHBOTS_PROTECT_RPC") or None,
    )

def private_rpc_url(chain_id: int):
    cfg = load_mev_config(chain_id)
    if not cfg.enabled: return None
    return cfg.private_rpc or cfg.flashbots_rpc

def submit_private_raw_tx(raw_tx_hex: str, chain_id: int):
    cfg = load_mev_config(chain_id)
    endpoint = cfg.flashbots_rpc or cfg.private_rpc
    if not endpoint or not cfg.enabled: return None
    if not raw_tx_hex.startswith("0x"): raw_tx_hex = "0x" + raw_tx_hex
    for method, params in [("eth_sendPrivateTransaction", [{"tx": raw_tx_hex}]), ("eth_sendRawTransaction", [raw_tx_hex])]:
        try:
            req = urllib.request.Request(endpoint, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if data.get("result"): return data["result"]
        except Exception as e:
            log.warning("private tx %s failed: %s", method, type(e).__name__)
    return None
