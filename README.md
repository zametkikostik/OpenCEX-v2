# OpenCEX-v2

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.14.0-green.svg)](./STATUS.md)
[![Chains](https://img.shields.io/badge/chains-ETH%20%7C%20BNB%20%7C%20Polygon%20%7C%20Arbitrum%20%7C%20Base-informational.svg)](#)
[![Docs RU](https://img.shields.io/badge/docs-Русский-blue.svg)](./README.ru.md)

**Modern infrastructure layer for the OpenCEX crypto exchange engine.**

Hybrid custody · multi-provider RPC · 0x liquidity · ZK-KYC · non-custodial settlement · ERC-4337 · protocol fees · production ops.

> **License:** Proprietary Commercial — use, copy, or redistribution **without written permission is prohibited**.  
> Repository: [github.com/zametkikostik/OpenCEX-v2](https://github.com/zametkikostik/OpenCEX-v2)  
> **Русская версия:** [README.ru.md](./README.ru.md)

---

## Overview

OpenCEX-v2 extends the classic custodial OpenCEX stack with a modular, production-oriented layer:

| Capability | Package / artifact |
|------------|-------------------|
| Multi-provider RPC router | `opencex_rpc` |
| 0x hybrid liquidity | `opencex_liquidity` |
| Swap REST + keeper pipeline | `opencex_swap_api` |
| Celery tasks & Django models | `opencex_django` |
| Zero-Knowledge KYC | `opencex_kyc` |
| Hybrid wallet / EIP-712 | `opencex_wallet` |
| NC on-chain settlement | `opencex_settlement` + `contracts/` |
| ERC-4337 UserOp + paymaster | `opencex_aa` |
| Secrets (Vault / KMS) | `opencex_secrets` |
| Prometheus metrics | `opencex_metrics` |
| MEV protection | `opencex_mev` |
| Protocol fee | `opencex_fees` |
| Circuit breaker & risk limits | `opencex_risk` |
| Observability | `observability/` |
| Staging & custody ops | `ops/` |

**Supported chains:** Ethereum, BNB Chain, Polygon, Arbitrum, Base (+ Sepolia / Base Sepolia for testnet).

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           Clients / UI               │
                    │  Nuxt · React · Vue · WalletConnect  │
                    └───────────────┬─────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
                    │     OpenCEX-backend (Django)         │
                    │  + opencex_* apps (this repository)  │
                    └───────┬─────────────┬───────────────┘
           custodial        │             │        non-custodial
    ┌───────────────────────▼──┐     ┌────▼────────────────────┐
    │ BalanceManager + Keeper  │     │ EIP-712 · Settlement V2 │
    │ Celery execute_swap      │     │ User wallet / AA        │
    │ Private RPC (MEV)        │     │ 0x quote → user signs   │
    └─────────────┬────────────┘     └────────────┬────────────┘
                  │                               │
         ┌────────▼────────┐              ┌───────▼────────┐
         │ Multi-RPC router│              │ Bundler / PM   │
         │ dRPC Ankr …     │              │ EntryPoint     │
         └─────────────────┘              └────────────────┘
```

**Funds model**

- **Custodial:** balances in OpenCEX DB; on-chain via exchange keeper.
- **Non-custodial:** assets stay in the user wallet until the user signs.

---

## Quick start

### 1. Install

```bash
git clone https://github.com/zametkikostik/OpenCEX-v2.git
cd OpenCEX-v2
pip install -e .
pip install -e ".[django,celery,metrics]"   # optional extras
```

### 2. Configure

```bash
cp .env.example .env
chmod 600 .env
# ZEROX_API_KEY, RPC_*_URLS, keeper keys (testnet), KYC, PROTOCOL_*
```

### 3. Wire into OpenCEX-backend

```python
# settings
from opencex_django.settings_patch import apply_opencex_v2
apply_opencex_v2(globals())

# urls
from opencex_django.urls_patch import opencex_v2_urlpatterns
urlpatterns += opencex_v2_urlpatterns
```

```bash
python manage.py migrate opencex_django
celery -A exchange worker -l info
```

Full staging procedure: **[ops/STAGING_CHECKLIST.md](ops/STAGING_CHECKLIST.md)**

---

## Core modules

### RPC router (`opencex_rpc`)

Latency-aware routing across **dRPC, Grove (Pocket), Ankr, Lava, GetBlock, NOWNodes, 1RPC**, and public fallbacks. Health scoring and circuit breaker included.

### Liquidity & swap

- 0x Swap API quotes / calldata  
- Hybrid routing (internal book + external liquidity)  
- REST: quote · preview · async execute (Celery keeper)

### Keeper

Lock balance → optional allowance → sign → **private RPC broadcast (MEV)** → credit buy / unlock on failure.

### ZK-KYC (`opencex_kyc`)

**zkMe** (primary), zkPass, Privado ID. Gates for withdraw and large custodial swaps.

### Settlement

EIP-712 NC orders · `OpenCEXSettlement` / **V2** with **protocol fee** (5–10 bps → issuer treasury) · Foundry tests.

### Account abstraction (`opencex_aa`)

UserOperation builder, bundler client, paymaster (`PAYMASTER_URL` or verifying paymaster).

### Risk & fees

```bash
OPENCEX_CIRCUIT_BREAKER=1
RISK_MAX_SWAP_USD=10000
PROTOCOL_FEE_BPS=5
PROTOCOL_TREASURY=0x...
MEV_PROTECT=1
PRIVATE_RPC_URL=https://rpc.flashbots.net
```

---

## API surface

| Method | Path | Purpose |
|--------|------|--------|
| POST | `/api/v1/swap/quote/` | Quote |
| POST | `/api/v1/swap/execute/` | Queue custodial swap |
| GET | `/api/v1/swap/execution/<id>/` | Status |
| POST | `/api/v1/wallet/swap/nc/` | NC quote |
| POST | `/api/v1/settlement/plan/` | Settlement plan |
| POST | `/api/v1/settlement/aa/userop/` | UserOp (+ paymaster) |
| * | `/api/v1/kyc/` | ZK-KYC |
| GET | `/metrics/` | Prometheus |

---

## Observability

```bash
docker compose -f observability/docker-compose.yml up -d
# Grafana :3000 (admin / opencex) · Prometheus :9091
```

Dashboard: `observability/grafana/opencex-dashboard.json`  
Alerts: `observability/prometheus/alerts.yml`

---

## Contracts & testnet

```bash
cd contracts && forge install foundry-rs/forge-std --no-commit && forge test -vv

FEE_RECIPIENT=0x... DEPLOYER_PRIVATE_KEY=0x... \
  ./scripts/deploy_settlement_testnet.sh sepolia
```

| Contract | Role |
|----------|------|
| `OpenCEXSettlement.sol` | NC fill (v1) |
| `OpenCEXSettlementV2.sol` | Fill + protocol fee |
| `OpenCEXStaking.sol` | Utility staking |

---

## Business model

See **[docs/BUSINESS_MODEL.md](docs/BUSINESS_MODEL.md)**: white-label franchise, **0.05%–0.1%** protocol fee, optional utility staking.

---

## Production readiness

| Layer | Status |
|-------|--------|
| Architecture & modules | Implemented |
| Staging templates & runbooks | `ops/` |
| Mainnet with customer funds | After staging, audit, custody ops, legal |

- [STAGING_CHECKLIST.md](ops/STAGING_CHECKLIST.md)  
- [CUSTODY_RUNBOOK.md](ops/CUSTODY_RUNBOOK.md)  
- [RUNBOOK_INCIDENTS.md](ops/RUNBOOK_INCIDENTS.md)  
- [SECURITY_AUDIT_CHECKLIST.md](ops/SECURITY_AUDIT_CHECKLIST.md)  

```bash
PYTHONPATH=. python scripts/testnet_smoke.py --offline
python ops/scripts/staging_e2e.py --base-url https://staging/api/v1 --token "$JWT" --quote
```

---

## Project layout

```
OpenCEX-v2/
├── opencex_rpc/          # Multi-provider RPC
├── opencex_liquidity/    # 0x + hybrid router
├── opencex_swap_api/     # REST + keeper
├── opencex_django/       # Models, Celery, patches
├── opencex_kyc/          # ZK-KYC
├── opencex_wallet/       # Hybrid wallet / EIP-712
├── opencex_settlement/   # NC settlement
├── opencex_aa/           # ERC-4337 + paymaster
├── opencex_secrets/      # Vault / KMS
├── opencex_metrics/      # Prometheus
├── opencex_mev/          # Private relays
├── opencex_fees/         # Protocol fee
├── opencex_risk/         # Circuit breaker + limits
├── contracts/            # Solidity + Foundry
├── observability/        # Prometheus, Grafana
├── ops/                  # Runbooks, staging, e2e
├── scripts/              # Smoke & deploy
├── docs/                 # Business model
├── frontend/             # NC swap UI samples
└── tests/
```

---

## Development

```bash
pip install -e ".[dev,metrics]"
pytest tests/ -v
```

Python **≥ 3.10**. Optional: Django 3.2+, Celery 5+, `prometheus_client`, Foundry.

---

## Security

- No production private keys in git or images  
- Vault AppRole or KMS-wrapped keeper keys  
- `MEV_PROTECT` + private RPC for custodial broadcasts  
- On-chain fee cap (`MAX_FEE_BPS`)  
- External audit of settlement/staking before mainnet  

---

## License

**Proprietary Commercial License.**

Copyright © zametkikostik. All rights reserved.

You may not use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of this software without **prior written permission** from the copyright holder.

---

## Status

See **[STATUS.md](STATUS.md)**.

Built as a professional drop-in modernization layer for OpenCEX — not a turnkey licensed exchange. Production deployment is the operator’s responsibility (infrastructure, compliance, audits, key custody).
