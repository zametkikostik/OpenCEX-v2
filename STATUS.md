# OpenCEX-v2 status v0.10.0

## Done
- HSM/Vault secrets (env, dotenv, Vault, AWS SM, KMS)
- Keeper key resolve + patch_keeper
- .env.example layout
- testnet smoke: scripts/testnet_smoke.py

## Smoke
```bash
PYTHONPATH=. python scripts/testnet_smoke.py --chain sepolia
PYTHONPATH=. python scripts/testnet_smoke.py --offline  # no network
```
