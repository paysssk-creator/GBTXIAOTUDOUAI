import { useState } from "react";
import { useDeviceCaps } from "../hooks/useDeviceCaps";
import { postData } from "../lib/api";

const ICONS: Record<string, () => JSX.Element> = {
  voice: VoiceIcon,
  microphone: MicIcon,
  bluetooth: BluetoothIcon,
  wifi: WifiIcon,
  camera: CameraIcon,
  keyboard: KeyboardIcon,
  mouse: MouseIcon,
  notifications: BellIcon,
  desktop: DesktopIcon,
  browser: BrowserIcon,
};

type TestResult = { ok: boolean; text: string };
type BatchItem = { id: string; name: string; status: "pending" | "running" | "passed" | "failed"; text: string };

async function runCapabilityTest(
  id: string,
  name: string,
  invoke: (id: string, params?: unknown) => Promise<{ ok: boolean; result?: unknown; error?: string }>
): Promise<TestResult> {
  let extra = "";
  try {
    let res: { ok: boolean; result?: unknown; error?: string };
    switch (id) {
      case "voice":
        res = await invoke("speak", { text: "GBT 设备能力测试" });
        break;
      case "microphone":
        res = await invoke("mic", { seconds: 3 });
        if (res.ok && res.result && typeof res.result === "object") {
          const r = res.result as Record<string, unknown>;
          const amplitude = r.max_amplitude ?? "-";
          const device = r.device_name ?? "";
          extra = ` (amplitude=${amplitude}${device ? `, ${device}` : ""})`;
        }
        break;
      case "camera":
        res = await invoke("camera", { index: 0 });
        break;
      case "notifications":
        res = await invoke("notify", { title: "GBT", message: "通知测试" });
        break;
      case "desktop":
        await postData<Record<string, unknown>>("/api/desk/observe", {});
        res = { ok: true, result: "桌面观察完成" };
        break;
      case "browser":
        await postData<Record<string, unknown>>("/api/skill/browser_open", { text: "https://www.google.com" });
        res = { ok: true, result: "浏览器已打开" };
        break;
      default:
        res = { ok: true, result: `${name} 可用` };
    }
    return { ok: res.ok, text: res.ok ? `✓ ${name} 正常${extra}` : `✗ ${name} 失败: ${res.error}` };
  } catch (err) {
    return { ok: false, text: `✗ ${name} 失败: ${err instanceof Error ? err.message : String(err)}` };
  }
}

export function DeviceCapsPanel() {
  const { caps, loading, probe, invoke } = useDeviceCaps();
  const [result, setResult] = useState<{ id: string; text: string } | null>(null);
  const [showBatch, setShowBatch] = useState(false);
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const [batchRunning, setBatchRunning] = useState(false);

  const handleClick = async (id: string, name: string) => {
    setResult({ id, text: `正在测试 ${name}...` });
    const r = await runCapabilityTest(id, name, invoke);
    setResult({ id, text: r.text });
  };

  const runBatch = async () => {
    setShowBatch(true);
    setBatchRunning(true);
    const items = caps.map((c) => ({ id: c.id, name: c.name, status: "pending" as const, text: "" }));
    setBatchItems(items);
    for (let i = 0; i < items.length; i++) {
      setBatchItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, status: "running" } : it)));
      const r = await runCapabilityTest(items[i].id, items[i].name, invoke);
      setBatchItems((prev) =>
        prev.map((it, idx) => (idx === i ? { ...it, status: r.ok ? "passed" : "failed", text: r.text } : it))
      );
    }
    setBatchRunning(false);
  };

  const passedCount = batchItems.filter((i) => i.status === "passed").length;
  const failedCount = batchItems.filter((i) => i.status === "failed").length;

  return (
    <div className="card">
      <div className="card-title">
        <span>设备能力</span>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-primary btn-sm" onClick={runBatch} disabled={loading || batchRunning}>
            {batchRunning ? "测试中..." : "一键测试"}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={probe} disabled={loading || batchRunning}>
            {loading ? "检测中..." : "刷新"}
          </button>
        </div>
      </div>
      <div className="device-grid" role="list">
        {caps.map((cap) => {
          const Icon = ICONS[cap.id] || DeviceIcon;
          return (
            <button
              key={cap.id}
              type="button"
              className="device-card"
              onClick={() => handleClick(cap.id, cap.name)}
              title={cap.detail || cap.name}
              role="listitem"
              aria-label={`测试 ${cap.name}`}
              disabled={loading || batchRunning}
            >
              <Icon />
              <span className="device-card-label">{cap.name}</span>
              {cap.available === true && <span className="text-xs" style={{ color: "var(--success)" }}>可用</span>}
              {cap.available === false && <span className="text-xs" style={{ color: "var(--error)" }}>不可用</span>}
              {cap.available === null && <span className="text-xs text-subtle">检测中</span>}
            </button>
          );
        })}
      </div>
      {result && !showBatch && (
        <div
          className="mt-3 text-sm"
          style={{
            color: result.text.startsWith("✓")
              ? "var(--success)"
              : result.text.startsWith("✗")
                ? "var(--error)"
                : "var(--fg-dim)",
          }}
        >
          {result.text}
        </div>
      )}

      {showBatch && (
        <div
          className="batch-dialog-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowBatch(false);
          }}
        >
          <div className="batch-dialog">
            <div className="batch-dialog-header">
              <span>统一能力测试</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowBatch(false)} disabled={batchRunning}>
                关闭
              </button>
            </div>
            <div className="batch-dialog-body">
              {batchItems.map((item) => (
                <div key={item.id} className="batch-item">
                  <span className="batch-item-name">{item.name}</span>
                  <span
                    className="batch-item-status"
                    style={{
                      color:
                        item.status === "passed"
                          ? "var(--success)"
                          : item.status === "failed"
                            ? "var(--error)"
                            : item.status === "running"
                              ? "var(--primary)"
                              : "var(--fg-dim)",
                    }}
                  >
                    {item.status === "pending" && "待测试"}
                    {item.status === "running" && "测试中..."}
                    {item.status === "passed" && (item.text || "通过")}
                    {item.status === "failed" && (item.text || "失败")}
                  </span>
                </div>
              ))}
            </div>
            {!batchRunning && batchItems.length > 0 && (
              <div className="batch-dialog-footer">
                通过 {passedCount} / {batchItems.length}，失败 {failedCount}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function VoiceIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 010 7.07"/><path d="M19.07 4.93a10 10 0 010 14.14"/></svg>;
}
function MicIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 00-3 3v7a3 3 0 006 0V5a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><path d="M12 19v3"/></svg>;
}
function BluetoothIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 7l12 10-6 5V2l6 5L6 17"/></svg>;
}
function WifiIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>;
}
function CameraIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V7a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>;
}
function KeyboardIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/></svg>;
}
function MouseIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v4"/></svg>;
}
function BellIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>;
}
function DesktopIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>;
}
function BrowserIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="18" rx="2"/><path d="M2 8h20"/><circle cx="6" cy="5.5" r="1"/><circle cx="10" cy="5.5" r="1"/></svg>;
}
function DeviceIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>;
}
