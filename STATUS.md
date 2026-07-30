# v0.13.0

MEV + protocol fee + staking contracts + Prometheus/Grafana docker-compose + testnet deploy script.
See docs/BUSINESS_MODEL.md

```bash
docker compose -f observability/docker-compose.yml up -d
FEE_RECIPIENT=0x.. DEPLOYER_PRIVATE_KEY=0x.. ./scripts/deploy_settlement_testnet.sh sepolia
```
