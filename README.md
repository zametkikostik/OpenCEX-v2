# OpenCEX-v2

**Modern infrastructure layer for the OpenCEX crypto exchange engine.**

Hybrid custody · multi-provider RPC · 0x liquidity · ZK-KYC · non-custodial settlement · ERC-4337 · protocol fees · production ops.

> **License:** Proprietary Commercial — use, copy, or redistribution **without written permission is prohibited**.  
> Repository: [github.com/zametkikostik/OpenCEX-v2](https://github.com/zametkikostik/OpenCEX-v2)

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
# optional
pip install -e ".[django,celery,metrics]"
```

### 2. Configure

```bash
cp .env.example .env
chmod 600 .env
# set ZEROX_API_KEY, RPC_*_URLS, keeper keys (testnet), etc.
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
Backend notes: **[integration/OPEN_CEX_BACKEND.md](integration/OPEN_CEX_BACKEND.md)**

---

## Core modules

### RPC router (`opencex_rpc`)

Latency-aware routing across dRPC, Grove (Pocket), Ankr, Lava, GetBlock, NOWNodes, 1RPC, and public fallbacks. Circuit breaker and health scoring included.

### Liquidity & swap (`opencex_liquidity`, `opencex_swap_api`)

- 0x Swap API quotes / calldata  
- Hybrid routing (internal book + external liquidity)  
- REST: quote · preview · async execute  

### Keeper

Custodial path: lock balance → optional allowance → sign → **private RPC broadcast** → credit buy / unlock on failure.

### ZK-KYC (`opencex_kyc`)

Providers: **zkMe** (primary), zkPass, Privado ID. Gates for withdraw and large custodial swaps.

### Settlement (`opencex_settlement`, `contracts/`)

- EIP-712 NC orders  
- `OpenCEXSettlement` / **V2** with **protocol fee** (5–10 bps → issuer treasury)  
- Foundry tests under `contracts/test/`

### Account abstraction (`opencex_aa`)

UserOperation builder, bundler client, paymaster attachment (`PAYMASTER_URL` or verifying paymaster).

### Risk & fees

```bash
OPENCEX_CIRCUIT_BREAKER=1          # halt custodial trading
RISK_MAX_SWAP_USD=10000
PROTOCOL_FEE_BPS=5
PROTOCOL_TREASURY=0x...
MEV_PROTECT=1
PRIVATE_RPC_URL=https://rpc.flashbots.net
```

---

## API surface (typical mount)

| Method | Path | Purpose |
|--------|------|--------|
| POST | `/api/v1/swap/quote/` | Firm / indicative quote |
| POST | `/api/v1/swap/execute/` | Queue custodial swap (Celery) |
| GET | `/api/v1/swap/execution/<id>/` | Execution status |
| POST | `/api/v1/wallet/swap/nc/` | NC quote for user wallet |
| POST | `/api/v1/settlement/plan/` | NC settlement plan + calldata |
| POST | `/api/v1/settlement/aa/userop/` | Build UserOp (+ paymaster) |
| * | `/api/v1/kyc/` | ZK-KYC session / status |
| GET | `/metrics/` | Prometheus scrape |

Exact paths depend on your `urls` include layout.

---

## Observability

```bash
docker compose -f observability/docker-compose.yml up -d
# Grafana  http://localhost:3000  (admin / opencex)
# Prometheus http://localhost:9091
```

- Dashboard: `observability/grafana/opencex-dashboard.json`  
- Alert rules: `observability/prometheus/alerts.yml`  

Metrics include RPC latency/errors, swap executions, keeper results, KYC events, AA/paymaster.

---

## Contracts & testnet

```bash
cd contracts
forge install foundry-rs/forge-std --no-commit
forge test -vv

FEE_RECIPIENT=0x... DEPLOYER_PRIVATE_KEY=0x... \
  ./scripts/deploy_settlement_testnet.sh sepolia
```

| Contract | Role |
|----------|------|
| `OpenCEXSettlement.sol` | NC fill (v1) |
| `OpenCEXSettlementV2.sol` | Fill + protocol fee |
| `OpenCEXStaking.sol` | Utility staking vault |

---

## Business model (summary)

Documented in **[docs/BUSINESS_MODEL.md](docs/BUSINESS_MODEL.md)**:

- White-label / franchise (Pay-to-Deploy + SaaS)  
- Protocol fee **0.05%–0.1%** on on-chain settlement fills → issuer treasury  
- Optional staking for fee tiers / collateral (not aggressive yield farming)  

---

## Production readiness

| Layer | Status |
|-------|--------|
| Architecture & modules | Implemented |
| Staging templates & runbooks | `ops/` |
| Mainnet with customer funds | **Only after** real staging, contract audit, custody ops, and legal compliance |

Essential ops docs:

- [STAGING_CHECKLIST.md](ops/STAGING_CHECKLIST.md)  
- [CUSTODY_RUNBOOK.md](ops/CUSTODY_RUNBOOK.md)  
- [RUNBOOK_INCIDENTS.md](ops/RUNBOOK_INCIDENTS.md)  
- [SECURITY_AUDIT_CHECKLIST.md](ops/SECURITY_AUDIT_CHECKLIST.md)  

```bash
# offline smoke
PYTHONPATH=. python scripts/testnet_smoke.py --offline

# against staging API
python ops/scripts/staging_e2e.py --base-url https://staging/api/v1 --token "$JWT" --quote
```

---

## Project layout

```
OpenCEX-v2/
├── opencex_rpc/          # Multi-provider RPC
├── opencex_liquidity/    # 0x + hybrid router
├── opencex_swap_api/     # REST + keeper
├── opencex_django/       # Models, Celery, integration patches
├── opencex_kyc/          # ZK-KYC providers
├── opencex_wallet/       # Hybrid wallet / EIP-712
├── opencex_settlement/   # NC settlement service
├── opencex_aa/           # ERC-4337 + paymaster
├── opencex_secrets/      # Vault / KMS / dotenv
├── opencex_metrics/      # Prometheus
├── opencex_mev/          # Private relay helpers
├── opencex_fees/         # Protocol fee + reconciliation
├── opencex_risk/         # Circuit breaker + limits
├── contracts/            # Solidity + Foundry tests
├── observability/        # Prometheus, Grafana, compose
├── ops/                  # Runbooks, staging, e2e
├── scripts/              # Smoke & deploy helpers
├── docs/                 # Business model & design notes
├── frontend/             # NC swap UI samples
└── tests/                # Pytest
```

---

## Development

```bash
pip install -e ".[dev,metrics]"
pytest tests/ -v
PYTHONPATH=. python scripts/testnet_smoke.py --chain sepolia --offline
```

Python **≥ 3.10**. Optional: Django 3.2+, Celery 5+, `prometheus_client`, Foundry for contracts.

---

## Security

- No production private keys in git or images  
- Prefer Vault AppRole or KMS-wrapped keeper keys  
- Enable `MEV_PROTECT` and private RPC for custodial broadcasts  
- Cap protocol fee on-chain (`MAX_FEE_BPS`)  
- External audit of settlement/staking contracts before mainnet  

See [ops/SECURITY_AUDIT_CHECKLIST.md](ops/SECURITY_AUDIT_CHECKLIST.md) and [ops/CUSTODY_RUNBOOK.md](ops/CUSTODY_RUNBOOK.md).

---

## License

**Proprietary Commercial License.**

Copyright © zametkikostik. All rights reserved.

You may not use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of this software without **prior written permission** from the copyright holder.

---

## Status

Current version and changelog pointers: **[STATUS.md](STATUS.md)**.

Built as a professional drop-in modernization layer for OpenCEX — not a turnkey licensed exchange. Production deployment remains the operator’s responsibility (infrastructure, compliance, audits, and key custody).
