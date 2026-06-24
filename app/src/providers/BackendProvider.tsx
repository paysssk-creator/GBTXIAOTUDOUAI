import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { isTauri } from "../lib/tauri";
import { useAppStore } from "../store";

interface BackendContextValue {
  start: () => Promise<void>;
  restart: () => Promise<void>;
  stop: () => Promise<void>;
  status: "idle" | "starting" | "healthy" | "failed";
  logs: string[];
  error: string | null;
}

const BackendContext = createContext<BackendContextValue | null>(null);

export function BackendProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<BackendContextValue["status"]>("idle");
  const [error, setError] = useState<string | null>(null);
  const logsRef = useRef<string[]>([]);
  const [, forceUpdate] = useState({});

  const appendLog = useCallback((line: string) => {
    logsRef.current = [...logsRef.current.slice(-199), line];
    forceUpdate({});
  }, []);

  useEffect(() => {
    if (!isTauri()) return;

    let unlisten: (() => void) | undefined;
    const setup = async () => {
      unlisten = await listen<string>("backend-log", (event) => {
        appendLog(event.payload);
      });
    };
    setup();
    return () => unlisten?.();
  }, [appendLog]);

  const start = useCallback(async () => {
    if (!isTauri()) {
      setStatus("healthy");
      return;
    }
    setStatus("starting");
    setError(null);
    logsRef.current = [];
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
    <BackendContext.Provider value={{ start, restart, stop, status, logs: logsRef.current, error }}>
      {children}
    </BackendContext.Provider>
  );
}

export function useBackend() {
  const ctx = useContext(BackendContext);
  if (!ctx) throw new Error("useBackend must be used within BackendProvider");
  return ctx;
}

async function pollUntilReady(
  setStatus: (s: BackendContextValue["status"]) => void,
  setError: (e: string | null) => void,
  appendLog: (line: string) => void
) {
  const HEALTH_URL = "http://127.0.0.1:8765/api/health";
  const MAX_FAILS = 40;
  let failures = 0;

  while (failures < MAX_FAILS) {
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
    } catch {
      // ignore
    }
    failures++;
    appendLog(`[Health] waiting (${failures}/${MAX_FAILS})...`);
    await new Promise((r) => setTimeout(r, 800));
  }

  setStatus("failed");
  setError("后端健康检查超时");
  appendLog("[Error] backend health check timed out");
}
