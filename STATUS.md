# OpenCEX-v2 v0.12.0

- Grafana: observability/grafana/opencex-dashboard.json
- Foundry: contracts/test/OpenCEXSettlement.t.sol (forge test)
- Paymaster: opencex_aa/paymaster.py + AA userop endpoint attaches paymasterAndData

PAYMASTER_POLICY=sponsor_settlement|sponsor_all|none
PAYMASTER_URL / PAYMASTER_ADDRESS / PAYMASTER_SIGNER_KEY
