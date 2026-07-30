import React, { useCallback, useMemo, useState } from "react";
import { OpenCEXApi, type QuoteResult } from "../shared/api";
import { CHAINS, toWei } from "../shared/chains";
import {
  connectInjected, connectWalletConnect, switchChain, sendTx, approveToken, disconnectWC, type WalletState,
} from "../shared/walletconnect";

const TOKENS = ["ETH", "USDT", "USDC", "BNB", "MATIC"] as const;

export type NcSwapProps = {
  apiBase?: string;
  authToken?: string;
  wcProjectId?: string;
};

export function NcSwap({
  apiBase = "/api/v1",
  authToken,
  wcProjectId = (import.meta as any).env?.VITE_WC_PROJECT_ID || "",
}: NcSwapProps) {
  const api = useMemo(() => new OpenCEXApi(apiBase, authToken), [apiBase, authToken]);
  const [wallet, setWallet] = useState<WalletState>({ address: null, chainId: 1, provider: null });
  const [chainId, setChainId] = useState(1);
  const [sell, setSell] = useState("ETH");
  const [buy, setBuy] = useState("USDT");
  const [amount, setAmount] = useState("0.01");
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [status, setStatus] = useState("Ready.");
  const [statusKind, setStatusKind] = useState<"" | "ok" | "err">("");
  const [busy, setBusy] = useState(false);

  const setMsg = (msg: string, kind: "" | "ok" | "err" = "") => { setStatus(msg); setStatusKind(kind); };

  const onConnectMM = useCallback(async () => {
    try {
      const w = await connectInjected();
      setWallet(w); setChainId(w.chainId); setMsg("MetaMask connected.", "ok");
      if (w.address) await api.registerSession("non_custodial", w.address, w.chainId);
    } catch (e) { setMsg(String((e as Error).message), "err"); }
  }, [api]);

  const onConnectWC = useCallback(async () => {
    if (!wcProjectId) return setMsg("Set VITE_WC_PROJECT_ID for WalletConnect.", "err");
    try {
      setBusy(true);
      const w = await connectWalletConnect(wcProjectId, chainId);
      setWallet(w); setChainId(w.chainId); setMsg("WalletConnect connected.", "ok");
      if (w.address) await api.registerSession("non_custodial", w.address, w.chainId);
    } catch (e) { setMsg(String((e as Error).message), "err"); }
    finally { setBusy(false); }
  }, [api, chainId, wcProjectId]);

  const onDisconnect = () => {
    disconnectWC();
    setWallet({ address: null, chainId: 1, provider: null });
    setQuote(null); setMsg("Disconnected.");
  };

  const onQuote = async () => {
    if (!wallet.address) return setMsg("Connect wallet first.", "err");
    try {
      setBusy(true); setMsg("Fetching quote…");
      const q = await api.getNcQuote({ chainId, sell, buy, sellAmount: toWei(amount, sell), taker: wallet.address });
      setQuote(q);
      setMsg(q.needs_allowance ? "Quote ready — approval required." : "Quote ready.", "ok");
    } catch (e) { setQuote(null); setMsg("Quote failed: " + (e as Error).message, "err"); }
    finally { setBusy(false); }
  };

  const onSwap = async () => {
    if (!wallet.address || !wallet.provider || !quote?.transaction) return;
    try {
      setBusy(true);
      await switchChain(wallet.provider, chainId);
      if (quote.needs_allowance && quote.allowance_spender && quote.sell_token) {
        setMsg("Approve token in wallet…");
        await approveToken(wallet.provider, wallet.address, quote.sell_token, quote.allowance_spender);
      }
      setMsg("Confirm swap in wallet…");
      const hash = await sendTx(wallet.provider, wallet.address, quote.transaction);
      setMsg("Submitted: " + hash, "ok");
    } catch (e) { setMsg("Swap failed: " + (e as Error).message, "err"); }
    finally { setBusy(false); }
  };

  const short = wallet.address ? `${wallet.address.slice(0, 6)}…${wallet.address.slice(-4)}` : "Not connected";

  return (
    <div style={s.card}>
      <h1 style={s.h1}>Non-Custodial Swap</h1>
      <p style={s.sub}>Funds stay in your wallet · 0x + OpenCEX · WC v2</p>
      <div style={s.wallet}>{short}</div>
      <label style={s.label}>Network</label>
      <select style={s.input} value={chainId} onChange={(e) => setChainId(Number(e.target.value))}>
        {Object.entries(CHAINS).map(([id, c]) => <option key={id} value={id}>{c.name}</option>)}
      </select>
      <div style={s.pair}>
        <div><label style={s.label}>Sell</label>
          <select style={s.input} value={sell} onChange={(e) => setSell(e.target.value)}>{TOKENS.map((t) => <option key={t}>{t}</option>)}</select></div>
        <div style={{ paddingBottom: 12, color: "#848e9c" }}>→</div>
        <div><label style={s.label}>Buy</label>
          <select style={s.input} value={buy} onChange={(e) => setBuy(e.target.value)}>{TOKENS.map((t) => <option key={t}>{t}</option>)}</select></div>
      </div>
      <label style={s.label}>Amount</label>
      <input style={s.input} value={amount} onChange={(e) => setAmount(e.target.value)} />
      {quote && <div style={s.price}>You receive ≈ {quote.buy_amount || "?"} (raw)</div>}
      {!wallet.address ? (
        <>
          <button style={s.btnSec} onClick={onConnectMM} disabled={busy}>MetaMask</button>
          <button style={s.btnPrim} onClick={onConnectWC} disabled={busy}>WalletConnect</button>
        </>
      ) : (
        <>
          <button style={s.btnSec} onClick={onDisconnect}>Disconnect</button>
          <button style={s.btnPrim} onClick={onQuote} disabled={busy}>Get Quote</button>
          <button style={s.btnPrim} onClick={onSwap} disabled={busy || !quote}>Swap</button>
        </>
      )}
      <div style={{ ...s.status, ...(statusKind === "ok" ? s.ok : {}), ...(statusKind === "err" ? s.err : {}) }}>{status}</div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  card: { width: "100%", maxWidth: 420, background: "#12161c", border: "1px solid #1e2329", borderRadius: 16, padding: 24, color: "#eaecef", fontFamily: "system-ui, sans-serif" },
  h1: { fontSize: "1.25rem", margin: "0 0 4px" },
  sub: { color: "#848e9c", fontSize: "0.85rem", marginBottom: 20 },
  wallet: { fontSize: "0.75rem", color: "#0ecb81", marginBottom: 12 },
  label: { display: "block", fontSize: "0.75rem", color: "#848e9c", margin: "12px 0 6px" },
  input: { width: "100%", padding: "12px 14px", borderRadius: 8, border: "1px solid #1e2329", background: "#0b0e11", color: "#eaecef", fontSize: "1rem" },
  pair: { display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 8, alignItems: "end" },
  btnPrim: { width: "100%", padding: 14, marginTop: 8, border: "none", borderRadius: 10, background: "#f0b90b", color: "#000", fontWeight: 600, cursor: "pointer" },
  btnSec: { width: "100%", padding: 14, marginTop: 8, border: "none", borderRadius: 10, background: "#1e2329", color: "#eaecef", fontWeight: 600, cursor: "pointer" },
  price: { fontSize: "0.9rem", color: "#848e9c", marginTop: 8 },
  status: { marginTop: 16, padding: 12, borderRadius: 8, background: "#0b0e11", fontSize: "0.8rem", color: "#848e9c", wordBreak: "break-all" },
  ok: { color: "#0ecb81", border: "1px solid #0ecb81" },
  err: { color: "#f6465d", border: "1px solid #f6465d" },
};

export default NcSwap;
