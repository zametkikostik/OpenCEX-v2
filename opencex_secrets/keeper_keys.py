from __future__ import annotations
import logging, os
from typing import Optional
from .loader import get_secret
log = logging.getLogger("opencex_secrets.keeper")
CHAIN_ENV = {1: "ETH_KEEPER_PRIVATE_KEY", 56: "BNB_KEEPER_PRIVATE_KEY", 137: "MATIC_KEEPER_PRIVATE_KEY",
             42161: "ARB_KEEPER_PRIVATE_KEY", 8453: "BASE_KEEPER_PRIVATE_KEY"}

def resolve_keeper_private_key(chain_id: int) -> Optional[str]:
    env_name = CHAIN_ENV.get(chain_id)
    if not env_name: return None
    pk = get_secret(env_name)
    if pk: return _normalize_pk(pk)
    path = os.getenv(f"OPENCEX_KEEPER_KEY_FILE_{chain_id}") or os.getenv("OPENCEX_KEEPER_KEY_FILE")
    if path and os.path.isfile(path):
        mode = os.stat(path).st_mode & 0o777
        if mode & 0o077:
            log.error("Keeper key file permissions too open"); return None
        return _normalize_pk(open(path).read().strip())
    log.error("Keeper key not found chain=%s", chain_id)
    return None

def _normalize_pk(pk: str) -> str:
    pk = pk.strip()
    if not pk.startswith("0x"): pk = "0x" + pk
    return pk
