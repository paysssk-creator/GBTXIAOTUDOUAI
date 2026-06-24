import { useCallback, useEffect, useState } from "react";
import { fetchJSON, postJSON } from "../lib/api";

export interface DeviceCapability {
  id: string;
  name: string;
  available: boolean | null;
  detail?: string;
}

const DEFAULT_CAPS: DeviceCapability[] = [
  { id: "voice", name: "语音播报", available: null },
  { id: "microphone", name: "麦克风", available: null },
  { id: "bluetooth", name: "蓝牙", available: null },
  { id: "wifi", name: "WiFi", available: null },
  { id: "camera", name: "摄像头", available: null },
  { id: "keyboard", name: "键盘", available: null },
  { id: "mouse", name: "鼠标", available: null },
  { id: "notifications", name: "通知", available: null },
  { id: "desktop", name: "桌面控制", available: null },
  { id: "browser", name: "浏览器", available: null },
];

export function useDeviceCaps() {
  const [caps, setCaps] = useState<DeviceCapability[]>(DEFAULT_CAPS);
  const [loading, setLoading] = useState(false);

  const probe = useCallback(async () => {
    setLoading(true);
    try {
      const result = (await fetchJSON("/api/device/probe")) as {
        capabilities?: Record<string, { available: boolean; detail?: string }>;
      };
      const map = result.capabilities || {};
      setCaps((prev) =>
        prev.map((c) => ({
          ...c,
          available: map[c.id]?.available ?? null,
          detail: map[c.id]?.detail,
        }))
      );
    } catch (err) {
      setCaps((prev) => prev.map((c) => ({ ...c, available: false, detail: String(err) })));
    } finally {
      setLoading(false);
    }
  }, []);

  const invoke = useCallback(async (id: string, params?: unknown) => {
    try {
      const result = await postJSON(`/api/device/${id}`, params ?? {});
      return { ok: true, result };
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  }, []);

  useEffect(() => {
    probe();
  }, [probe]);

  return { caps, loading, probe, invoke };
}
