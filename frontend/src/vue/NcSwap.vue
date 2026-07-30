<script setup lang="ts">
import { computed, ref } from "vue";
import { OpenCEXApi, type QuoteResult } from "../shared/api";
import { CHAINS, toWei } from "../shared/chains";
import {
  connectInjected, connectWalletConnect, switchChain, sendTx, approveToken, disconnectWC, type WalletState,
} from "../shared/walletconnect";

const props = withDefaults(defineProps<{ apiBase?: string; authToken?: string; wcProjectId?: string }>(), {
  apiBase: "/api/v1",
  authToken: "",
  wcProjectId: (import.meta as any).env?.VITE_WC_PROJECT_ID || "",
});

const TOKENS = ["ETH", "USDT", "USDC", "BNB", "MATIC"];
const api = computed(() => new OpenCEXApi(props.apiBase, props.authToken || undefined));
const wallet = ref<WalletState>({ address: null, chainId: 1, provider: null });
const chainId = ref(1);
const sell = ref("ETH");
const buy = ref("USDT");
const amount = ref("0.01");
const quote = ref<QuoteResult | null>(null);
const status = ref("Ready.");
const statusKind = ref<"" | "ok" | "err">("");
const busy = ref(false);

function setMsg(msg: string, kind: "" | "ok" | "err" = "") { status.value = msg; statusKind.value = kind; }
const short = computed(() =>
  wallet.value.address ? `${wallet.value.address.slice(0, 6)}…${wallet.value.address.slice(-4)}` : "Not connected"
);

async function onConnectMM() {
  try {
    const w = await connectInjected();
    wallet.value = w; chainId.value = w.chainId; setMsg("MetaMask connected.", "ok");
    if (w.address) await api.value.registerSession("non_custodial", w.address, w.chainId);
  } catch (e) { setMsg(String((e as Error).message), "err"); }
}

async function onConnectWC() {
  if (!props.wcProjectId) return setMsg("Set VITE_WC_PROJECT_ID for WalletConnect.", "err");
  try {
    busy.value = true;
    const w = await connectWalletConnect(props.wcProjectId, chainId.value);
    wallet.value = w; chainId.value = w.chainId; setMsg("WalletConnect connected.", "ok");
    if (w.address) await api.value.registerSession("non_custodial", w.address, w.chainId);
  } catch (e) { setMsg(String((e as Error).message), "err"); }
  finally { busy.value = false; }
}

function onDisconnect() {
  disconnectWC();
  wallet.value = { address: null, chainId: 1, provider: null };
  quote.value = null; setMsg("Disconnected.");
}

async function onQuote() {
  if (!wallet.value.address) return setMsg("Connect wallet first.", "err");
  try {
    busy.value = true; setMsg("Fetching quote…");
    const q = await api.value.getNcQuote({
      chainId: chainId.value, sell: sell.value, buy: buy.value,
      sellAmount: toWei(amount.value, sell.value), taker: wallet.value.address,
    });
    quote.value = q;
    setMsg(q.needs_allowance ? "Quote ready — approval required." : "Quote ready.", "ok");
  } catch (e) { quote.value = null; setMsg("Quote failed: " + (e as Error).message, "err"); }
  finally { busy.value = false; }
}

async function onSwap() {
  if (!wallet.value.address || !wallet.value.provider || !quote.value?.transaction) return;
  try {
    busy.value = true;
    await switchChain(wallet.value.provider, chainId.value);
    const q = quote.value;
    if (q.needs_allowance && q.allowance_spender && q.sell_token) {
      setMsg("Approve token in wallet…");
      await approveToken(wallet.value.provider, wallet.value.address, q.sell_token, q.allowance_spender);
    }
    setMsg("Confirm swap in wallet…");
    const hash = await sendTx(wallet.value.provider, wallet.value.address, q.transaction!);
    setMsg("Submitted: " + hash, "ok");
  } catch (e) { setMsg("Swap failed: " + (e as Error).message, "err"); }
  finally { busy.value = false; }
}
</script>

<template>
  <div class="card">
    <h1>Non-Custodial Swap</h1>
    <p class="sub">Funds stay in your wallet · 0x + OpenCEX · WC v2</p>
    <div class="wallet">{{ short }}</div>
    <label>Network</label>
    <select v-model.number="chainId">
      <option v-for="(c, id) in CHAINS" :key="id" :value="Number(id)">{{ c.name }}</option>
    </select>
    <div class="pair">
      <div><label>Sell</label><select v-model="sell"><option v-for="t in TOKENS" :key="t">{{ t }}</option></select></div>
      <div class="arrow">→</div>
      <div><label>Buy</label><select v-model="buy"><option v-for="t in TOKENS" :key="t">{{ t }}</option></select></div>
    </div>
    <label>Amount</label>
    <input v-model="amount" type="text" />
    <div v-if="quote" class="price">You receive ≈ {{ quote.buy_amount || "?" }} (raw)</div>
    <template v-if="!wallet.address">
      <button class="btn-sec" :disabled="busy" @click="onConnectMM">MetaMask</button>
      <button class="btn-prim" :disabled="busy" @click="onConnectWC">WalletConnect</button>
    </template>
    <template v-else>
      <button class="btn-sec" @click="onDisconnect">Disconnect</button>
      <button class="btn-prim" :disabled="busy" @click="onQuote">Get Quote</button>
      <button class="btn-prim" :disabled="busy || !quote" @click="onSwap">Swap</button>
    </template>
    <div class="status" :class="statusKind">{{ status }}</div>
  </div>
</template>

<style scoped>
.card { width: 100%; max-width: 420px; background: #12161c; border: 1px solid #1e2329; border-radius: 16px; padding: 24px; color: #eaecef; font-family: system-ui, sans-serif; }
h1 { font-size: 1.25rem; margin: 0 0 4px; }
.sub { color: #848e9c; font-size: 0.85rem; margin-bottom: 20px; }
.wallet { font-size: 0.75rem; color: #0ecb81; margin-bottom: 12px; }
label { display: block; font-size: 0.75rem; color: #848e9c; margin: 12px 0 6px; }
select, input { width: 100%; padding: 12px 14px; border-radius: 8px; border: 1px solid #1e2329; background: #0b0e11; color: #eaecef; font-size: 1rem; }
.pair { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; align-items: end; }
.arrow { color: #848e9c; padding-bottom: 12px; text-align: center; }
button { width: 100%; padding: 14px; margin-top: 8px; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; }
.btn-prim { background: #f0b90b; color: #000; }
.btn-prim:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sec { background: #1e2329; color: #eaecef; }
.price { font-size: 0.9rem; color: #848e9c; margin-top: 8px; }
.status { margin-top: 16px; padding: 12px; border-radius: 8px; background: #0b0e11; font-size: 0.8rem; color: #848e9c; word-break: break-all; }
.status.ok { color: #0ecb81; border: 1px solid #0ecb81; }
.status.err { color: #f6465d; border: 1px solid #f6465d; }
</style>
