import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  root: resolve(__dirname),
  publicDir: "public",
  envPrefix: "VITE_",
  server: {
    port: 5174,
    host: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist/vue",
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/vue/main.ts"),
      name: "OpenCEXNcSwap",
      formats: ["es", "umd"],
      fileName: (format) => `opencex-nc-swap-vue.${format}.js`,
    },
    rollupOptions: {
      external: ["vue"],
      output: { globals: { vue: "Vue" } },
    },
  },
  define: { "process.env": {} },
});
