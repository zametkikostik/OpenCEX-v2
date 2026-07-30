"""Layered secrets: env → dotenv → Vault KV2 → AWS SM → KMS unwrap."""
from __future__ import annotations
import json, logging, os, threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
log = logging.getLogger("opencex_secrets")
_lock = threading.Lock()
_cache: Dict[str, str] = {}

def _read_dotenv(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file(): return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'").strip('"')
        if k and k not in os.environ: out[k] = v
    return out

def _vault_token() -> Optional[str]:
    t = os.getenv("VAULT_TOKEN")
    if t: return t
    role_id, secret_id, addr = os.getenv("VAULT_ROLE_ID"), os.getenv("VAULT_SECRET_ID"), os.getenv("VAULT_ADDR")
    if not (role_id and secret_id and addr): return None
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{addr.rstrip('/')}/v1/auth/approle/login",
            data=json.dumps({"role_id": role_id, "secret_id": secret_id}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("auth", {}).get("client_token")
    except Exception as e:
        log.warning("Vault AppRole login failed: %s", type(e).__name__); return None

def _vault_get(path: str, key: str) -> Optional[str]:
    addr = os.getenv("VAULT_ADDR")
    if not addr: return None
    token = _vault_token()
    if not token: return None
    try:
        import urllib.request
        req = urllib.request.Request(f"{addr.rstrip('/')}/v1/{path.lstrip('/')}", headers={"X-Vault-Token": token})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        body = data.get("data") or {}
        if "data" in body and isinstance(body["data"], dict): body = body["data"]
        val = body.get(key)
        return str(val) if val is not None else None
    except Exception as e:
        log.warning("Vault read failed: %s", type(e).__name__); return None

def _aws_sm_get(secret_id: str, key: Optional[str] = None) -> Optional[str]:
    try:
        import boto3
        raw = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id).get("SecretString") or ""
        if key and raw.startswith("{"): return str(json.loads(raw).get(key) or "") or None
        return raw or None
    except Exception as e:
        log.warning("AWS SM failed: %s", type(e).__name__); return None

def _kms_decrypt(ciphertext_b64: str) -> Optional[str]:
    try:
        import base64, boto3
        out = boto3.client("kms").decrypt(CiphertextBlob=base64.b64decode(ciphertext_b64))
        return out["Plaintext"].decode("utf-8")
    except Exception as e:
        log.warning("KMS decrypt failed: %s", type(e).__name__); return None

@dataclass
class Secrets:
    source: str = "env"
    _data: Dict[str, str] = field(default_factory=dict)
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self._data: return self._data[key]
        return os.getenv(key, default)
    def require(self, key: str) -> str:
        v = self.get(key)
        if not v: raise KeyError(f"Missing required secret: {key}")
        return v
    def mask(self, key: str) -> str:
        v = self.get(key) or ""
        return "***" if len(v) < 8 else v[:4] + "…" + v[-2:]

def load_secrets(dotenv_path: Optional[str] = None, vault_mount_path: Optional[str] = None) -> Secrets:
    data: Dict[str, str] = {}
    source = "env"
    env_file = dotenv_path or os.getenv("OPENCEX_ENV_FILE") or ".env"
    dotenv = _read_dotenv(Path(env_file))
    if dotenv:
        data.update(dotenv); source = "dotenv+env"
        if os.getenv("OPENCEX_SECRETS_INJECT_ENV", "1") == "1":
            for k, v in dotenv.items(): os.environ.setdefault(k, v)
    mount = vault_mount_path or os.getenv("VAULT_SECRET_PATH", "secret/data/opencex")
    if os.getenv("VAULT_ADDR"):
        for key in ("ETH_KEEPER_PRIVATE_KEY", "BNB_KEEPER_PRIVATE_KEY", "MATIC_KEEPER_PRIVATE_KEY",
                    "ARB_KEEPER_PRIVATE_KEY", "BASE_KEEPER_PRIVATE_KEY", "ZEROX_API_KEY", "ZKME_API_KEY", "ZKME_APP_ID"):
            val = _vault_get(mount, key)
            if val:
                data[key] = val; source = "vault"
                if os.getenv("OPENCEX_SECRETS_INJECT_ENV", "1") == "1": os.environ.setdefault(key, val)
    aws_name = os.getenv("AWS_SECRET_NAME")
    if aws_name:
        for key in ("ETH_KEEPER_PRIVATE_KEY", "ZEROX_API_KEY"):
            val = _aws_sm_get(aws_name, key)
            if val: data[key] = val; source = "aws_sm"
    for env_key, val in list(os.environ.items()):
        if env_key.endswith("_KMS_CIPHERTEXT") and val:
            plain_key = env_key[: -len("_KMS_CIPHERTEXT")]
            plain = _kms_decrypt(val)
            if plain:
                data[plain_key] = plain; source = "kms"
                if os.getenv("OPENCEX_SECRETS_INJECT_ENV", "1") == "1": os.environ.setdefault(plain_key, plain)
    with _lock: _cache.update(data)
    log.info("Secrets loaded source=%s keys=%s", source, sorted(data.keys()))
    return Secrets(source=source, _data=data)

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    with _lock:
        if key in _cache: return _cache[key]
    v = os.getenv(key)
    if v: return v
    val = _vault_get(os.getenv("VAULT_SECRET_PATH", "secret/data/opencex"), key)
    if val:
        with _lock: _cache[key] = val
        return val
    return default
