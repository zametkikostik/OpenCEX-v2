import EthereumProvider from "@walletconnect/ethereum-provider";
import { CHAINS, type ChainId } from "./chains";

export type WalletState = {
  address: string | null;
  chainId: number;
  provider: EthereumProvider | { request: (args: { method: string; params?: unknown[] }) => Promise<unknown> } | null;
};

let wcProvider: EthereumProvider | null = null;

export async function connectWalletConnect(projectId: string, defaultChainId = 1): Promise<WalletState> {
  const chains = Object.keys(CHAINS).map(Number);
  const rpcMap: Record<number, string> = {};
  for (const [id, c] of Object.entries(CHAINS)) rpcMap[Number(id)] = c.rpc;

  wcProvider = await EthereumProvider.init({
    projectId,
    chains: [defaultChainId],
    optionalChains: chains.filter((c) => c !== defaultChainId),
    showQrModal: true,
    rpcMap,
    metadata: {
      name: "OpenCEX",
      description: "OpenCEX Non-Custodial Swap",
      url: typeof window !== "undefined" ? window.location.origin : "https://opencex.local",
      icons: ["https://avatars.githubusercontent.com/u/37784886"],
    },
  });

  await wcProvider.enable();
  return {
    address: wcProvider.accounts[0] || null,
    chainId: Number(wcProvider.chainId),
    provider: wcProvider,
  };
}

export async function connectInjected(): Promise<WalletState> {
  const eth = (window as unknown as { ethereum?: { request: Function } }).ethereum;
  if (!eth) throw new Error("No injected wallet (install MetaMask)");
  const accounts = (await eth.request({ method: "eth_requestAccounts" })) as string[];
  const chainHex = (await eth.request({ method: "eth_chainId" })) as string;
  return {
    address: accounts[0] || null,
    chainId: parseInt(chainHex, 16),
    provider: eth as WalletState["provider"],
  };
}

export async function switchChain(provider: WalletState["provider"], chainId: number): Promise<void> {
  if (!provider) return;
  const hex = "0x" + chainId.toString(16);
  try {
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hex }] });
  } catch (e: unknown) {
    const err = e as { code?: number };
    if (err.code === 4902) {
      const c = CHAINS[chainId as ChainId];
      if (!c) throw e;
      await provider.request({
        method: "wallet_addEthereumChain",
        params: [{
          chainId: hex,
          chainName: c.name,
          rpcUrls: [c.rpc],
          nativeCurrency: c.nativeCurrency,
          blockExplorerUrls: [c.explorer],
        }],
      });
    } else throw e;
  }
}

export async function sendTx(
  provider: WalletState["provider"],
  from: string,
  tx: { to: string; data: string; value?: string | number; gas?: string | number }
): Promise<string> {
  if (!provider) throw new Error("No provider");
  const params: Record<string, string> = {
    from, to: tx.to, data: tx.data,
    value: tx.value ? "0x" + BigInt(tx.value).toString(16) : "0x0",
  };
  if (tx.gas) params.gas = "0x" + Number(tx.gas).toString(16);
  return (await provider.request({ method: "eth_sendTransaction", params: [params] })) as string;
}

export async function approveToken(
  provider: WalletState["provider"], from: string, token: string, spender: string
): Promise<string> {
  const max = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";
  const data = "0x095ea7b3" + spender.slice(2).toLowerCase().padStart(64, "0") + max;
  return sendTx(provider, from, { to: token, data });
}

export function disconnectWC() {
  if (wcProvider) { wcProvider.disconnect(); wcProvider = null; }
}
