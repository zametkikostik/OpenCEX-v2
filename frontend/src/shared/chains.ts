export const CHAINS = {
  1: { chainId: 1, name: "Ethereum", rpc: "https://eth.llamarpc.com", explorer: "https://etherscan.io", nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 } },
  56: { chainId: 56, name: "BNB Chain", rpc: "https://bsc-dataseed.binance.org", explorer: "https://bscscan.com", nativeCurrency: { name: "BNB", symbol: "BNB", decimals: 18 } },
  137: { chainId: 137, name: "Polygon", rpc: "https://polygon-rpc.com", explorer: "https://polygonscan.com", nativeCurrency: { name: "MATIC", symbol: "MATIC", decimals: 18 } },
  42161: { chainId: 42161, name: "Arbitrum", rpc: "https://arb1.arbitrum.io/rpc", explorer: "https://arbiscan.io", nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 } },
  8453: { chainId: 8453, name: "Base", rpc: "https://mainnet.base.org", explorer: "https://basescan.org", nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 } },
} as const;

export type ChainId = keyof typeof CHAINS;

export const DECIMALS: Record<string, number> = {
  ETH: 18, BNB: 18, MATIC: 18, USDT: 6, USDC: 6, DAI: 18,
};

export function toWei(amount: string, symbol: string): string {
  const d = DECIMALS[symbol] ?? 18;
  const [whole, frac = ""] = amount.split(".");
  const fracPadded = (frac + "0".repeat(d)).slice(0, d);
  return BigInt(whole + fracPadded).toString();
}
