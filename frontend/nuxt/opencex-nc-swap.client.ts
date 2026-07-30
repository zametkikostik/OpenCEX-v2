/** Nuxt client plugin — mounts NC Swap on #opencex-nc-swap */
import { defineNuxtPlugin } from "#app";

export default defineNuxtPlugin(async (nuxtApp) => {
  if (process.server) return;

  const config = useRuntimeConfig?.() || { public: {} as Record<string, string> };
  const publicCfg = (config as { public?: Record<string, string> }).public || {};

  nuxtApp.provide("opencexNcSwap", {
    async mount(selector = "#opencex-nc-swap") {
      const el = document.querySelector(selector) as HTMLElement | null;
      if (!el) return null;
      const { createApp } = await import("vue");
      const mod = await import("../src/vue/NcSwap.vue");
      const NcSwap = mod.default;
      const apiBase = el.dataset.apiBase || publicCfg.opencexApiBase || publicCfg.API_BASE || "/api/v1";
      const authToken = el.dataset.token || publicCfg.opencexToken || "";
      const wcProjectId = el.dataset.wcProjectId || publicCfg.wcProjectId || publicCfg.VITE_WC_PROJECT_ID || "";
      const app = createApp(NcSwap, { apiBase, authToken, wcProjectId });
      app.mount(el);
      return app;
    },
  });

  if (document.getElementById("opencex-nc-swap")) {
    // @ts-expect-error provided
    await nuxtApp.$opencexNcSwap?.mount?.();
  }
});
