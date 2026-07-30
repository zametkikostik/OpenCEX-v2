from __future__ import annotations
import logging, os
log = logging.getLogger("opencex_secrets.patch")

def install() -> None:
    from opencex_secrets.loader import load_secrets
    from opencex_secrets.keeper_keys import resolve_keeper_private_key
    load_secrets()
    try:
        import opencex_swap_api.keeper as keeper_mod
    except ImportError:
        return
    original = keeper_mod.load_keeper_config
    def load_keeper_config_secure(chain_id: int):
        cfg = original(chain_id)
        if cfg is not None: return cfg
        pk = resolve_keeper_private_key(chain_id)
        if not pk: return None
        key_map = {1: "ETH_KEEPER_PRIVATE_KEY", 56: "BNB_KEEPER_PRIVATE_KEY", 137: "MATIC_KEEPER_PRIVATE_KEY",
                   42161: "ARB_KEEPER_PRIVATE_KEY", 8453: "BASE_KEEPER_PRIVATE_KEY"}
        env_name = key_map.get(chain_id)
        if env_name and not os.getenv(env_name): os.environ[env_name] = pk
        return original(chain_id)
    keeper_mod.load_keeper_config = load_keeper_config_secure
    log.info("Keeper config loader patched with secrets backend")
