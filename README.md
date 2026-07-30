# OpenCEX RPC Router

Production-ready **multi-provider RPC layer** for OpenCEX.

Replaces hard-coded Infura and single-endpoint connections with a resilient router that supports:

- **dRPC**
- **Grove (Pocket Network)**
- **Ankr**
- **Lava Network**
- **GetBlock**
- **NOWNodes**
- **1RPC**
- Custom URLs + public fallbacks

### Features

- Latency-based + health-score routing
- Circuit breaker (auto disable bad endpoints)
- Automatic failover
- Per-chain configuration (ETH, BNB, Polygon, Arbitrum, Base)
- Drop-in `Web3` instances
- Zero secrets in code (env-only)

---

## Install

```bash
pip install -e .
# or
pip install web3 requests
```

## Configuration (environment)

```bash
# Recommended – pick at least 2–3 providers
export DRPC_API_KEY=your_drpc_key
export ANKR_API_KEY=your_ankr_key
export GROVE_APP_ID=your_grove_app_id
export GROVE_API_KEY=your_grove_key          # optional
export LAVA_API_KEY=your_lava_key
export GETBLOCK_API_KEY=your_getblock_token
export NOWNODES_API_KEY=your_nownodes_key

# Optional toggles
export USE_1RPC=true
export USE_PUBLIC_RPCS=true                  # last-resort public endpoints

# Or inject full URL lists
export RPC_ETH_URLS=https://my-eth-1.com,https://my-eth-2.com
export RPC_BNB_URLS=https://my-bsc.com
export RPC_POLYGON_URLS=...
export RPC_ARBITRUM_URLS=...
export RPC_BASE_URLS=...
```

## Usage

```python
from opencex_rpc import get_web3, w3_eth, w3_bnb, health, failover

# Ethereum
w3 = get_web3(1)
print(w3.eth.block_number)

# Shortcuts
print(w3_eth().eth.block_number)
print(w3_bnb().eth.block_number)

# Health snapshot
print(health(1))          # only Ethereum providers
print(health())           # all chains

# Force failover
w3 = failover(1)
```

## Integration into OpenCEX-backend

### 1. Install the package

```bash
cd /app/opencex/backend
pip install -e /path/to/opencex-rpc
```

### 2. Replace Infura helper

**Old** (`cryptocoins/utils/infura.py`):

```python
from web3 import Web3
from django.conf import settings

def get_web3():
    provider = HTTPProvider(f'https://mainnet.infura.io/v3/{settings.INFURA_API_KEY}')
    return Web3(provider)

w3 = get_web3()
```

**New**:

```python
from opencex_rpc import get_web3 as _get_web3

def get_web3():
    return _get_web3(chain_id=1)

# Lazy – do not create at import time in production
# w3 = get_web3()   # prefer calling get_web3() when needed
```

### 3. Replace BNB connection

**Old** (`cryptocoins/coins/bnb/connection.py`) → simplify to:

```python
from opencex_rpc import get_web3

def get_w3_connection():
    return get_web3(chain_id=56)
```

### 4. Ethereum manager

In `cryptocoins/coins/eth/ethereum.py`:

```python
from opencex_rpc import get_web3

# instead of: from cryptocoins.utils.infura import w3
w3 = get_web3(1)
ethereum_manager = EthereumManager(client=w3)
```

Same pattern for Polygon (`137`), Arbitrum (`42161`), Base (`8453`).

### 5. Django settings / .env

Add the provider keys to your `.env` (see list above).  
You can remove `INFURA_API_KEY` after migration.

### 6. Optional health endpoint

```python
# e.g. in admin_rest or a monitoring view
from opencex_rpc import health
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def rpc_health(request):
    chain_id = request.query_params.get("chain_id")
    data = health(int(chain_id)) if chain_id else health()
    return Response(data)
```

---

## Design notes

| Component | Responsibility |
|-----------|----------------|
| `config.py` | Chains + provider list from env |
| `models.py` | ProviderConfig, ProviderHealth, CircuitState |
| `health.py` | Circuit breaker + scoring |
| `router.py` | Selection, failover, Web3 factory |
| `client.py` | Shortcuts & constants |

Circuit breaker states:

- **CLOSED** – normal
- **OPEN** – disabled after N consecutive errors
- **HALF_OPEN** – probe after recovery timeout

Score formula (simplified):

```
score = (1000 / avg_latency_ms) * (weight/100) - error_penalty - priority_bias
```

---

## Roadmap

- [ ] WebSocket providers
- [ ] Redis-backed health (multi-process)
- [ ] Prometheus metrics exporter
- [ ] Solana / TON adapters
- [ ] Request coalescing / batching

## License

**Proprietary Commercial License.**

All rights reserved. Unauthorized use, copying, modification, or distribution
is strictly prohibited without a written commercial license from the copyright holder.

See [LICENSE](LICENSE) for full terms.
