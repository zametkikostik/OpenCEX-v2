# OpenCEX-v2 v0.11.0

## Prometheus
- opencex_metrics (RPC, swap, keeper, KYC)
- GET /metrics/ or OPENCEX_METRICS_PORT=9090
- pip install prometheus_client

## NC Settlement
- EIP-712 NCOrder + OpenCEXSettlement.sol
- POST /api/v1/settlement/plan/
- SETTLEMENT_CONTRACT_<chain_id>

## ERC-4337
- UserOpBuilder + BundlerClient
- POST /api/v1/settlement/aa/userop/
- BUNDLER_URL, ENTRYPOINT_<chain>
