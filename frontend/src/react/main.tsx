import React from "react";
import { createRoot } from "react-dom/client";
import { NcSwap } from "./NcSwap";

const el = document.getElementById("opencex-nc-swap");
if (el) {
  const apiBase = el.dataset.apiBase || (import.meta as any).env?.VITE_API_BASE || "/api/v1";
  const authToken = el.dataset.token || "";
  const wcProjectId = el.dataset.wcProjectId || (import.meta as any).env?.VITE_WC_PROJECT_ID || "";
  createRoot(el).render(
    <React.StrictMode>
      <NcSwap apiBase={apiBase} authToken={authToken || undefined} wcProjectId={wcProjectId} />
    </React.StrictMode>
  );
}

export { NcSwap };
