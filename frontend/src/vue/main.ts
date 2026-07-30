import { createApp } from "vue";
import NcSwap from "./NcSwap.vue";

const el = document.getElementById("opencex-nc-swap");
if (el) {
  const apiBase = el.dataset.apiBase || (import.meta as any).env?.VITE_API_BASE || "/api/v1";
  const authToken = el.dataset.token || "";
  const wcProjectId = el.dataset.wcProjectId || (import.meta as any).env?.VITE_WC_PROJECT_ID || "";
  createApp(NcSwap, { apiBase, authToken, wcProjectId }).mount(el);
}

export { default as NcSwap } from "./NcSwap.vue";
