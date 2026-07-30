# Phase 4 — Hybrid Wallet

## Modes

| Mode | Keys | Funds |
|------|------|-------|
| custodial | Exchange | On exchange |
| non_custodial | User only | User wallet |
| hybrid | Both | Optional deposits |

## REST

- POST `/api/v1/wallet/session/`
- POST `/api/v1/wallet/order/build/` — EIP-712
- POST `/api/v1/wallet/order/submit/`
- POST `/api/v1/wallet/swap/nc/` — 0x for user wallet

## Keeper (custodial)

See `opencex_swap_api/keeper.py`. Set `ETH_KEEPER_PRIVATE_KEY`, optional `PRIVATE_RPC_URL` for MEV protection.

## ZK mint + MEV

ZK-KYC does not mint on-chain by default. If you mint attestations later, use private RPC / Flashbots Protect.

## License

Proprietary Commercial.
