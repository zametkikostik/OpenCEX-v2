# Integrate NC Swap into OpenCEX Nuxt frontend

1. Copy `src/vue/NcSwap.vue` + `src/shared/*` into frontend
2. Copy `nuxt/opencex-nc-swap.client.ts` → `plugins/opencex-nc-swap.client.js`
3. Copy `nuxt/pages-quick-swap.vue` → `pages/quick-swap.vue`
4. Set `WC_PROJECT_ID` / `OPENCEX_API_BASE`
5. Add `@walletconnect/ethereum-provider`

See full notes in this folder.
