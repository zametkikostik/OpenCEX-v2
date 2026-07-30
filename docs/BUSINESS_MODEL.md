# Monetization & B2B SaaS

White-label Pay-to-Deploy + 5–10 bps protocol fee is solid. MEV protect is mandatory for keeper. Staking: utility first (fee tiers), not aggressive APY.

Env: PROTOCOL_FEE_BPS=5 PROTOCOL_TREASURY=0x... MEV_PROTECT=1 PRIVATE_RPC_URL=...

Contracts: OpenCEXSettlementV2 (fee), OpenCEXStaking
Ops: observability/docker-compose.yml + alerts.yml
Deploy: scripts/deploy_settlement_testnet.sh sepolia
