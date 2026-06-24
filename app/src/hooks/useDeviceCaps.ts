import { useCallback, useEffect, useState } from "react";
import { fetchData, postData } from "../lib/api";

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
      const map = await fetchData<Record<string, { available: boolean; detail?: string }>>("/api/device/probe");
      setCaps((prev) =>
        prev.map((c) => {
          const source = c.id === "keyboard" || c.id === "mouse" ? map["keyboard_mouse"] : map[c.id];
          return {
            ...c,
            available: source?.available ?? null,
            detail: source?.detail,
          };
        })
      );
    } catch (err) {
      setCaps((prev) => prev.map((c) => ({ ...c, available: false, detail: String(err) })));
    } finally {
      setLoading(false);
    }
  }, []);

  const invoke = useCallback(async (id: string, params?: unknown) => {
    try {
      const result = await postData<Record<string, unknown>>(`/api/device/${id}`, params ?? {});
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
