import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname),
  publicDir: "public",
  envPrefix: "VITE_",
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist/react",
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/react/main.tsx"),
      name: "OpenCEXNcSwap",
      formats: ["es", "umd"],
      fileName: (format) => `opencex-nc-swap.${format}.js`,
    },
    rollupOptions: {
      external: ["react", "react-dom"],
      output: { globals: { react: "React", "react-dom": "ReactDOM" } },
    },
  },
  define: { "process.env": {} },
});
