import { useState } from "react";
import { useDeviceCaps } from "../hooks/useDeviceCaps";

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

export function DeviceCapsPanel() {
  const { caps, loading, probe, invoke } = useDeviceCaps();
  const [result, setResult] = useState<{ id: string; text: string } | null>(null);

  const handleClick = async (id: string, name: string) => {
    setResult({ id, text: `正在测试 ${name}...` });
    let res;
    switch (id) {
      case "voice":
        res = await invoke("speak", { text: "GBT 设备能力测试" });
        break;
      case "microphone":
        res = await invoke("mic", { duration: 3 });
        break;
      case "camera":
        res = await invoke("camera", { frames: 1 });
        break;
      case "notifications":
        res = await invoke("notify", { title: "GBT", message: "通知测试" });
        break;
      default:
        res = { ok: true, result: `${name} 可用` };
    }
    setResult({
      id,
      text: res.ok ? `✓ ${name} 正常` : `✗ ${name} 失败: ${res.error}`,
    });
  };

  return (
    <div className="card">
      <div className="card-title">
        <span>设备能力</span>
        <button className="btn btn-ghost btn-sm" onClick={probe} disabled={loading}>
          {loading ? "检测中..." : "刷新"}
        </button>
      </div>
      <div className="device-grid">
        {caps.map((cap) => {
          const Icon = ICONS[cap.id] || DeviceIcon;
          return (
            <div
              key={cap.id}
              className="device-card"
              onClick={() => handleClick(cap.id, cap.name)}
              title={cap.detail || cap.name}
            >
              <Icon />
              <span className="device-card-label">{cap.name}</span>
              {cap.available === true && <span className="text-xs" style={{ color: "var(--success)" }}>可用</span>}
              {cap.available === false && <span className="text-xs" style={{ color: "var(--error)" }}>不可用</span>}
              {cap.available === null && <span className="text-xs text-subtle">检测中</span>}
            </div>
          );
        })}
      </div>
      {result && (
        <div className="mt-3 text-sm" style={{ color: result.text.startsWith("✓") ? "var(--success)" : "var(--fg-dim)" }}>
          {result.text}
        </div>
      )}
    </div>
  );
}

function VoiceIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 00-3 3v7a3 3 0 006 0V5a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><path d="M12 19v3"/></svg>;
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
