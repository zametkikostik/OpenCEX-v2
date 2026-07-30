# Secrets / HSM / Vault

Layers: env → `.env` → Vault KV2 → AWS SM → KMS `*_KMS_CIPHERTEXT` → chmod 600 key file.

```python
from opencex_secrets.loader import load_secrets
from opencex_secrets.patch_keeper import install
load_secrets(); install()
```

Boot via `opencex_django` AppConfig.ready.

Never log private keys. Prefer AppRole + short-lived tokens.
