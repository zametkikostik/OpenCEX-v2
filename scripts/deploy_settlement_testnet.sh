#!/usr/bin/env bash
set -euo pipefail
CHAIN="${1:-sepolia}"
FEE_RECIPIENT="${FEE_RECIPIENT:?set FEE_RECIPIENT}"
FEE_BPS="${FEE_BPS:-5}"
PK="${DEPLOYER_PRIVATE_KEY:?set DEPLOYER_PRIVATE_KEY}"
case "$CHAIN" in
  sepolia) RPC="${RPC_SEPOLIA_URLS%%,*}"; RPC="${RPC:-https://rpc.sepolia.org}"; CHAIN_ID=11155111 ;;
  base-sepolia) RPC="${RPC_BASE_SEPOLIA_URLS%%,*}"; RPC="${RPC:-https://sepolia.base.org}"; CHAIN_ID=84532 ;;
  *) echo "Usage: $0 sepolia|base-sepolia"; exit 1 ;;
esac
cd "$(dirname "$0")/../contracts"
command -v forge >/dev/null || { echo "Install Foundry"; exit 1; }
echo "Deploy OpenCEXSettlementV2 fee=$FEE_BPS recipient=$FEE_RECIPIENT chain=$CHAIN"
forge create OpenCEXSettlementV2 --rpc-url "$RPC" --private-key "$PK" \
  --constructor-args "$FEE_RECIPIENT" "$FEE_BPS" --broadcast
echo "SETTLEMENT_CONTRACT_${CHAIN_ID}=<address>"
echo "PROTOCOL_FEE_BPS=$FEE_BPS PROTOCOL_TREASURY=$FEE_RECIPIENT"
echo "MEV: PRIVATE_RPC_URL=https://rpc.flashbots.net"
