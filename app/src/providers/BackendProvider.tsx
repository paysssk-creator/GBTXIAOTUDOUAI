import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { isTauri } from "../lib/tauri";
import { useAppStore } from "../store";

interface BackendContextValue {
  start: () => Promise<void>;
  restart: () => Promise<void>;
  stop: () => Promise<void>;
  clearLogs: () => void;
  status: "idle" | "starting" | "healthy" | "failed";
  logs: string[];
  error: string | null;
  safeMode: boolean;
  enterSafeMode: () => void;
}

const BackendContext = createContext<BackendContextValue | null>(null);

export function BackendProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<BackendContextValue["status"]>("idle");
  const [error, setError] = useState<string | null>(null);
  const [safeMode, setSafeMode] = useState(false);
  const logsRef = useRef<string[]>([]);
  const [, forceUpdate] = useState({});
  const setBackendStatus = useAppStore((s) => s.setBackendStatus);

  const enterSafeMode = useCallback(() => {
    setSafeMode(true);
  }, []);

  const clearLogs = useCallback(() => {
    logsRef.current = [];
    forceUpdate({});
  }, []);

  const appendLog = useCallback((line: string) => {
    logsRef.current = [...logsRef.current.slice(-199), line];
    forceUpdate({});
  }, []);

  useEffect(() => {
    setBackendStatus(status);
  }, [status, setBackendStatus]);

  useEffect(() => {
    if (!isTauri()) return;

    const unsubs: (() => void)[] = [];

    const setup = async () => {
      const logUnlisten = await listen<string>("backend-log", (event) => {
        appendLog(event.payload);
      });
      unsubs.push(logUnlisten);

      const statusUnlisten = await listen<{ status: string; error?: string }>(
        "backend-status",
        (event) => {
          const payload = event.payload;
          const next = payload.status as BackendContextValue["status"];
          if (next === "idle" || next === "starting" || next === "healthy" || next === "failed") {
            setStatus(next);
            setError(payload.error || null);
            if (payload.error) {
              appendLog(`[Error] ${payload.error}`);
            }
          }
        }
      );
      unsubs.push(statusUnlisten);
    };

    setup();
    return () => {
      for (const unsub of unsubs) {
        unsub();
      }
    };
  }, [appendLog]);

  const start = useCallback(async () => {
    if (!isTauri()) {
      setStatus("healthy");
      return;
    }
    setStatus("starting");
    setError(null);
    logsRef.current = [];
    forceUpdate({});
    try {
      const info = (await invoke("start_backend")) as {
        port: number;
        data_dir: string;
        status: string;
      };
      useAppStore.getState().setBackendInfo({
        port: info.port,
        dataDir: info.data_dir,
      });
      appendLog(`[Tauri] backend started on port ${info.port}`);
      await pollUntilReady(setStatus, setError, appendLog);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("failed");
      appendLog(`[Error] ${msg}`);
    }
  }, [appendLog]);

  const restart = useCallback(async () => {
    if (!isTauri()) return;
    setStatus("starting");
    setError(null);
    logsRef.current = [];
    forceUpdate({});
    try {
      const info = (await invoke("restart_backend")) as {
        port: number;
        data_dir: string;
        status: string;
      };
      useAppStore.getState().setBackendInfo({
        port: info.port,
        dataDir: info.data_dir,
      });
      appendLog(`[Tauri] backend restarted on port ${info.port}`);
      await pollUntilReady(setStatus, setError, appendLog);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("failed");
      appendLog(`[Error] ${msg}`);
    }
  }, [appendLog]);

  const stop = useCallback(async () => {
    if (!isTauri()) return;
    try {
      await invoke("stop_backend");
      setStatus("idle");
      appendLog("[Tauri] backend stopped");
    } catch (err) {
      appendLog(`[Error] stop failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [appendLog]);

  return (
    <BackendContext.Provider
      value={{ start, restart, stop, clearLogs, status, logs: logsRef.current, error, safeMode, enterSafeMode }}
    >
      {children}
    </BackendContext.Provider>
  );
}

export function useBackend() {
  const ctx = useContext(BackendContext);
  if (!ctx) throw new Error("useBackend must be used within BackendProvider");
  return ctx;
}

import { HEALTH_URL } from "../lib/config";

async function pollUntilReady(
  setStatus: (s: BackendContextValue["status"]) => void,
  setError: (e: string | null) => void,
  appendLog: (line: string) => void
) {
  const MAX_ATTEMPTS = 40;
  const INITIAL_DELAY_MS = 400;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(HEALTH_URL, { signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok) {
        setStatus("healthy");
        setError(null);
        appendLog("[Health] backend ready");
        return;
      }
      appendLog(`[Health] HTTP ${res.status} (${attempt}/${MAX_ATTEMPTS})`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      appendLog(`[Health] not ready (${attempt}/${MAX_ATTEMPTS}): ${message}`);
    }
    const delay = Math.min(INITIAL_DELAY_MS * 2 ** Math.floor(attempt / 5), 3000);
    await new Promise((r) => setTimeout(r, delay));
  }

  setStatus("failed");
  setError("后端健康检查超时，请检查端口 8765 是否被占用或后端是否崩溃");
  appendLog("[Error] backend health check timed out");
}
