import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { isTauri } from "./lib/tauri";
import { BackendStatus, pollHealth } from "./lib/backend";

const DASHBOARD_URL = "http://127.0.0.1:8765/";

function App() {
  const [status, setStatus] = useState<BackendStatus>({
    state: "starting",
    message: "正在启动 GBT 后端...",
  });
  const [logs, setLogs] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const appendLog = (line: string) => {
    setLogs((prev) => [...prev.slice(-199), line]);
  };

  const monitorBackend = async (signal: AbortSignal) => {
    await pollHealth(
      (s) => {
        setStatus(s);
      },
      signal
    );
  };

  const startBackend = async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const abort = new AbortController();
    abortRef.current = abort;

    setStatus({ state: "starting", message: "正在启动 GBT 后端..." });
    setLogs([]);

    try {
      if (isTauri()) {
        const info = (await invoke("start_backend")) as {
          port: number;
          data_dir: string;
          status: string;
        };
        appendLog(`[Tauri] backend started: ${JSON.stringify(info)}`);
      } else {
        appendLog("[Web] running outside Tauri, skipping backend start");
      }

      await monitorBackend(abort.signal);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog(`[Error] ${msg}`);
      setStatus({ state: "error", message: msg });
    }
  };

  const restartBackend = async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const abort = new AbortController();
    abortRef.current = abort;

    setStatus({ state: "starting", message: "正在重启 GBT 后端..." });
    setLogs([]);

    try {
      if (isTauri()) {
        const info = (await invoke("restart_backend")) as {
          port: number;
          data_dir: string;
          status: string;
        };
        appendLog(`[Tauri] backend restarted: ${JSON.stringify(info)}`);
      } else {
        appendLog("[Web] running outside Tauri, skipping backend restart");
      }

      await monitorBackend(abort.signal);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog(`[Error] restart failed: ${msg}`);
      setStatus({ state: "error", message: msg });
    }
  };

  useEffect(() => {
    startBackend();
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Listen for backend log events from Rust
  useEffect(() => {
    if (!isTauri()) return;
    let unlisten: (() => void) | undefined;
    const setup = async () => {
      const { listen } = await import("@tauri-apps/api/event");
      unlisten = await listen<string>("backend-log", (event) => {
        appendLog(event.payload);
      });
    };
    setup();
    return () => {
      unlisten?.();
    };
  }, []);

  if (status.state === "ready") {
    return <iframe src={DASHBOARD_URL} title="GBT Dashboard" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />;
  }

  const dotClass = status.state === "error" ? "error" : "";

  return (
    <div className="shell">
      <div className="shell-card">
        <h1>GBT AI Workstation</h1>
        <p>
          <span className="status">
            <span className={`dot ${dotClass}`} />
            {status.message}
          </span>
        </p>
        {logs.length > 0 && (
          <div className="logs">{logs.join("\n")}</div>
        )}
        {status.state === "error" && (
          <button onClick={restartBackend}>重启后端</button>
        )}
      </div>
    </div>
  );
}

export default App;
