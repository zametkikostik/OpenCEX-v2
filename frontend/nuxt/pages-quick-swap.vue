<template>
  <div class="page">
    <h2 class="title">{{ $t ? $t('quick_swap') : 'Quick Swap' }}</h2>
    <p class="hint">Non-custodial · powered by 0x</p>
    <div
      id="opencex-nc-swap"
      :data-api-base="apiBase"
      :data-token="authToken"
      :data-wc-project-id="wcProjectId"
    />
  </div>
</template>

<script>
export default {
  name: "QuickSwapPage",
  data() { return { mountedApp: null }; },
  computed: {
    apiBase() {
      return (this.$config && this.$config.opencexApiBase) || process.env.OPENCEX_API_BASE || "/api/v1";
    },
    authToken() {
      try {
        return (this.$store && this.$store.state.auth && this.$store.state.auth.token) ||
          (typeof localStorage !== "undefined" && localStorage.getItem("token")) || "";
      } catch { return ""; }
    },
    wcProjectId() {
      return (this.$config && this.$config.wcProjectId) || process.env.WC_PROJECT_ID || "";
    },
  },
  async mounted() {
    try {
      if (this.$opencexNcSwap && this.$opencexNcSwap.mount) {
        this.mountedApp = await this.$opencexNcSwap.mount("#opencex-nc-swap");
        return;
      }
    } catch (_) {}
    try {
      const { createApp } = await import("vue");
      const mod = await import("../src/vue/NcSwap.vue");
      this.mountedApp = createApp(mod.default, {
        apiBase: this.apiBase, authToken: this.authToken, wcProjectId: this.wcProjectId,
      });
      this.mountedApp.mount("#opencex-nc-swap");
    } catch (e) { console.error("OpenCEX NC Swap mount failed", e); }
  },
  beforeDestroy() {
    if (this.mountedApp && this.mountedApp.unmount) this.mountedApp.unmount();
  },
};
</script>

<style scoped>
.page { max-width: 480px; margin: 40px auto; padding: 0 16px; }
.title { color: #eaecef; font-size: 1.5rem; margin-bottom: 4px; }
.hint { color: #848e9c; font-size: 0.9rem; margin-bottom: 24px; }
</style>
