# OpenCEX-v2

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Лицензия: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)](./LICENSE)
[![Версия](https://img.shields.io/badge/version-0.14.0-green.svg)](./STATUS.md)
[![Сети](https://img.shields.io/badge/сети-ETH%20%7C%20BNB%20%7C%20Polygon%20%7C%20Arbitrum%20%7C%20Base-informational.svg)](#)
[![English](https://img.shields.io/badge/docs-English-blue.svg)](./README.md)

**Современный инфраструктурный слой для движка криптобиржи OpenCEX.**

Гибридный кастоди · multi-provider RPC · ликвидность 0x · ZK-KYC · on-chain settlement · ERC-4337 · protocol fee · production ops.

> **Лицензия:** коммерческая proprietary — использование, копирование и распространение **без письменного разрешения запрещены**.  
> Репозиторий: [github.com/zametkikostik/OpenCEX-v2](https://github.com/zametkikostik/OpenCEX-v2)  
> **English:** [README.md](./README.md)

---

## Обзор

OpenCEX-v2 расширяет классический кастодиальный OpenCEX модульным production-слоем:

| Возможность | Пакет / артефакт |
|-------------|------------------|
| Multi-provider RPC-роутер | `opencex_rpc` |
| Гибридная ликвидность 0x | `opencex_liquidity` |
| Swap REST + keeper | `opencex_swap_api` |
| Celery и Django-модели | `opencex_django` |
| Zero-Knowledge KYC | `opencex_kyc` |
| Гибридный кошелёк / EIP-712 | `opencex_wallet` |
| NC on-chain settlement | `opencex_settlement` + `contracts/` |
| ERC-4337 UserOp + paymaster | `opencex_aa` |
| Секреты (Vault / KMS) | `opencex_secrets` |
| Prometheus-метрики | `opencex_metrics` |
| Защита от MEV | `opencex_mev` |
| Protocol fee | `opencex_fees` |
| Circuit breaker и лимиты | `opencex_risk` |
| Наблюдаемость | `observability/` |
| Staging и custody ops | `ops/` |

**Сети:** Ethereum, BNB Chain, Polygon, Arbitrum, Base (+ Sepolia / Base Sepolia).

---

## Архитектура

```
                    ┌─────────────────────────────────────┐
                    │           Клиенты / UI               │
                    │  Nuxt · React · Vue · WalletConnect  │
                    └───────────────┬─────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
                    │     OpenCEX-backend (Django)         │
                    │  + пакеты opencex_* (этот репозиторий)│
                    └───────┬─────────────┬───────────────┘
           кастодиальный    │             │    некастодиальный
    ┌───────────────────────▼──┐     ┌────▼────────────────────┐
    │ BalanceManager + Keeper  │     │ EIP-712 · Settlement V2 │
    │ Celery execute_swap      │     │ Кошелёк пользователя    │
    │ Private RPC (MEV)        │     │ 0x quote → подпись юзера│
    └─────────────┬────────────┘     └────────────┬────────────┘
                  │                               │
         ┌────────▼────────┐              ┌───────▼────────┐
         │ Multi-RPC router│              │ Bundler / PM   │
         │ dRPC Ankr …     │              │ EntryPoint     │
         └─────────────────┘              └────────────────┘
```

**Модель средств**

- **Кастоди:** балансы в БД OpenCEX; on-chain через keeper биржи.  
- **Некастоди:** активы остаются на кошельке пользователя до его подписи.

---

## Быстрый старт

### 1. Установка

```bash
git clone https://github.com/zametkikostik/OpenCEX-v2.git
cd OpenCEX-v2
pip install -e .
pip install -e ".[django,celery,metrics]"   # опционально
```

### 2. Конфигурация

```bash
cp .env.example .env
chmod 600 .env
# ZEROX_API_KEY, RPC_*_URLS, ключи keeper (testnet), KYC, PROTOCOL_*
```

### 3. Подключение к OpenCEX-backend

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

Полный staging: **[ops/STAGING_CHECKLIST.md](ops/STAGING_CHECKLIST.md)**

---

## Основные модули

### RPC-роутер (`opencex_rpc`)

Маршрутизация по задержке и health: **dRPC, Grove (Pocket), Ankr, Lava, GetBlock, NOWNodes, 1RPC** + публичные fallback. Circuit breaker.

### Ликвидность и swap

- Котировки / calldata 0x Swap API  
- Гибридный роутинг (внутренний стакан + внешняя ликвидность)  
- REST: quote · preview · async execute (Celery)

### Keeper

Блокировка баланса → allowance → подпись → **private RPC (MEV)** → зачисление / разблокировка при ошибке.

### ZK-KYC (`opencex_kyc`)

**zkMe** (основной), zkPass, Privado ID. Гейты на вывод и крупные кастодиальные свопы.

### Settlement

EIP-712 NC-ордера · `OpenCEXSettlement` / **V2** с **protocol fee** (5–10 bps → treasury эмитента) · тесты Foundry.

### Account Abstraction (`opencex_aa`)

Сборка UserOperation, клиент bundler, paymaster (`PAYMASTER_URL` или verifying).

### Риск и комиссии

```bash
OPENCEX_CIRCUIT_BREAKER=1          # стоп кастодиальных свопов
RISK_MAX_SWAP_USD=10000
PROTOCOL_FEE_BPS=5                 # 0.05%
PROTOCOL_TREASURY=0x...
MEV_PROTECT=1
PRIVATE_RPC_URL=https://rpc.flashbots.net
```

---

## API (типовой mount)

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/v1/swap/quote/` | Котировка |
| POST | `/api/v1/swap/execute/` | Очередь кастодиального swap |
| GET | `/api/v1/swap/execution/<id>/` | Статус |
| POST | `/api/v1/wallet/swap/nc/` | NC-котировка |
| POST | `/api/v1/settlement/plan/` | План settlement |
| POST | `/api/v1/settlement/aa/userop/` | UserOp (+ paymaster) |
| * | `/api/v1/kyc/` | ZK-KYC |
| GET | `/metrics/` | Prometheus |

---

## Наблюдаемость

```bash
docker compose -f observability/docker-compose.yml up -d
# Grafana :3000 (admin / opencex) · Prometheus :9091
```

Дашборд: `observability/grafana/opencex-dashboard.json`  
Алерты: `observability/prometheus/alerts.yml`

---

## Контракты и testnet

```bash
cd contracts && forge install foundry-rs/forge-std --no-commit && forge test -vv

FEE_RECIPIENT=0x... DEPLOYER_PRIVATE_KEY=0x... \
  ./scripts/deploy_settlement_testnet.sh sepolia
```

| Контракт | Роль |
|----------|------|
| `OpenCEXSettlement.sol` | NC fill (v1) |
| `OpenCEXSettlementV2.sol` | Fill + protocol fee |
| `OpenCEXStaking.sol` | Utility-стейкинг |

---

## Бизнес-модель

**[docs/BUSINESS_MODEL.md](docs/BUSINESS_MODEL.md):** white-label франшиза, **0.05%–0.1%** protocol fee, опциональный utility-стейкинг.

---

## Готовность к продакшену

| Слой | Статус |
|------|--------|
| Архитектура и модули | Реализовано |
| Шаблоны staging и runbooks | `ops/` |
| Mainnet с деньгами клиентов | Только после staging, аудита, custody и legal |

- [STAGING_CHECKLIST.md](ops/STAGING_CHECKLIST.md)  
- [CUSTODY_RUNBOOK.md](ops/CUSTODY_RUNBOOK.md)  
- [RUNBOOK_INCIDENTS.md](ops/RUNBOOK_INCIDENTS.md)  
- [SECURITY_AUDIT_CHECKLIST.md](ops/SECURITY_AUDIT_CHECKLIST.md)  

```bash
PYTHONPATH=. python scripts/testnet_smoke.py --offline
python ops/scripts/staging_e2e.py --base-url https://staging/api/v1 --token "$JWT" --quote
```

---

## Структура проекта

```
OpenCEX-v2/
├── opencex_rpc/          # Multi-provider RPC
├── opencex_liquidity/    # 0x + hybrid router
├── opencex_swap_api/     # REST + keeper
├── opencex_django/       # Модели, Celery, патчи
├── opencex_kyc/          # ZK-KYC
├── opencex_wallet/       # Гибридный кошелёк
├── opencex_settlement/   # NC settlement
├── opencex_aa/           # ERC-4337 + paymaster
├── opencex_secrets/      # Vault / KMS
├── opencex_metrics/      # Prometheus
├── opencex_mev/          # Private relay
├── opencex_fees/         # Protocol fee
├── opencex_risk/         # Circuit breaker + лимиты
├── contracts/            # Solidity + Foundry
├── observability/        # Prometheus, Grafana
├── ops/                  # Runbooks, staging, e2e
├── scripts/              # Smoke и deploy
├── docs/                 # Бизнес-модель
├── frontend/             # Примеры NC UI
└── tests/
```

---

## Разработка

```bash
pip install -e ".[dev,metrics]"
pytest tests/ -v
```

Python **≥ 3.10**. Опционально: Django 3.2+, Celery 5+, `prometheus_client`, Foundry.

---

## Безопасность

- Нет production private keys в git и образах  
- Vault AppRole или KMS для keeper  
- `MEV_PROTECT` + private RPC для кастодиальных broadcast  
- Ончейн-кап fee (`MAX_FEE_BPS`)  
- Внешний аудит settlement/staking до mainnet  

---

## Лицензия

**Proprietary Commercial License.**

Copyright © zametkikostik. Все права защищены.

Запрещается использовать, копировать, изменять, публиковать, распространять или продавать ПО **без предварительного письменного разрешения** правообладателя.

---

## Статус

См. **[STATUS.md](STATUS.md)**.

Профессиональный drop-in слой модернизации OpenCEX — не готовая лицензируемая биржа «под ключ». Вывод в прод — ответственность оператора (инфраструктура, compliance, аудиты, хранение ключей).
