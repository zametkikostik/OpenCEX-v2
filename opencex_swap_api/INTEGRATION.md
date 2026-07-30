# Swap REST API — Integration into OpenCEX-backend

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET/POST | `/api/v1/swap/preview/` | Public | Indicative price |
| POST | `/api/v1/swap/quote/` | Public | Firm quote + calldata |
| POST | `/api/v1/swap/execute/` | Login | Custodial execute plan |
| GET | `/api/v1/swap/tokens/` | Public | Token map per chain |
| GET | `/api/v1/swap/sources/` | Public | 0x liquidity sources |

## Install

```bash
pip install -e git+https://github.com/zametkikostik/OpenCEX-v2.git#egg=opencex-rpc
```

## Wire into backend

```python
# settings.py
INSTALLED_APPS += ["opencex_swap_api"]

# urls.py
path("api/v1/swap/", include("opencex_swap_api.urls")),
```

```bash
# .env
ZEROX_API_KEY=...
ETH_KEEPER_ADDRESS=0x...
BNB_KEEPER_ADDRESS=0x...
```

## Example

```bash
curl "https://exchange/api/v1/swap/preview/?chain_id=1&sell=ETH&buy=USDT&amount=1000000000000000000"

curl -X POST https://exchange/api/v1/swap/quote/ \
  -H "Content-Type: application/json" \
  -d '{"chain_id":1,"sell":"ETH","buy":"USDT","amount":"1000000000000000000","taker":"0x..."}'
```

## Custodial pipeline

1. Lock user sell balance
2. Approve allowance_spender if needed
3. Sign transaction with keeper
4. Broadcast via opencex_rpc
5. Credit buy balance

## License

Proprietary Commercial.
