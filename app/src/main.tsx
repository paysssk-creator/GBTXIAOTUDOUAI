import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { isTauri } from "./lib/tauri";
import { invoke } from "@tauri-apps/api/core";

function logToRust(level: "error" | "warn", message: string, stack?: string) {
  if (isTauri()) {
    invoke("log_frontend_error", { message: `[${level}] ${message}`, stack }).catch(() => {
      // ignore
    });
  }
}

window.addEventListener("error", (e) => {
  console.error("[window.onerror]", e.message, e.filename, e.lineno, e.colno, e.error);
  logToRust("error", e.message, e.error?.stack);
});

window.addEventListener("unhandledrejection", (e) => {
  console.error("[unhandledrejection]", e.reason);
  const reason = e.reason instanceof Error ? e.reason.message : String(e.reason);
  const stack = e.reason instanceof Error ? e.reason.stack : undefined;
  logToRust("error", reason, stack);
});

const root = document.getElementById("root");
if (!root) {
  console.error("[main] Root element not found");
  throw new Error("Root element not found");
}

try {
  createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
} catch (err) {
  console.error("[main] Failed to render app:", err);
  const message = err instanceof Error ? err.message : String(err);
  logToRust("error", message, err instanceof Error ? err.stack : undefined);
}
