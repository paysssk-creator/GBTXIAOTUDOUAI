const HEALTH_URL = "http://127.0.0.1:8765/api/health";
const POLL_INTERVAL_MS = 800;
const MAX_FAILS = 40;

export type BackendState = "starting" | "loading" | "ready" | "error";

export interface BackendStatus {
  state: BackendState;
  message: string;
}

export async function pollHealth(
  onStatus: (status: BackendStatus, logs: string[]) => void,
  signal: AbortSignal
): Promise<void> {
  let failures = 0;

  while (!signal.aborted) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(HEALTH_URL, { signal: controller.signal });
      clearTimeout(timeout);

      if (res.ok) {
        failures = 0;
        onStatus({ state: "ready", message: "后端已就绪" }, []);
        return;
      }
      failures++;
    } catch {
      failures++;
    }

    if (failures >= MAX_FAILS) {
      onStatus(
        { state: "error", message: "后端健康检查超时，请查看日志" },
        []
      );
      return;
    }

    onStatus(
      { state: "loading", message: `等待后端就绪 (${failures}/${MAX_FAILS})...` },
      []
    );
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}
