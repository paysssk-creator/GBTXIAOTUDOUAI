import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBackend } from "../providers/BackendProvider";
import { useCoreState } from "../providers/CoreStateProvider";
import { useToast } from "../providers/ToastProvider";
import { DeviceCapsPanel } from "../components/DeviceCapsPanel";
import { LLMMetricsPanel } from "../components/LLMMetricsPanel";

export default function Home() {
  const navigate = useNavigate();
  const { status, restart, error } = useBackend();
  const { showToast } = useToast();
  const { apiKeySet, model, version } = useCoreState();

  const isReady = status === "healthy";

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">欢迎回来</h1>
        <p className="page-subtitle">
          {isReady ? "GBT 后端运行正常" : "GBT 后端未就绪"}
          {version ? ` · ${version}` : ""}
          {model ? ` · 当前模型 ${model}` : ""}
        </p>
      </div>

      <div className="grid grid-2 mb-4">
        <div className="card">
          <div className="card-title">状态概览</div>
          <div className="flex items-center gap-3 mb-3">
            <span className={`status-pill ${isReady ? "ready" : apiKeySet ? "warning" : "error"}`}>
              <span className="status-dot" />
              {isReady ? "运行中" : apiKeySet ? "未就绪" : "未登录"}
            </span>
            {!apiKeySet && <span className="text-sm text-dim">请在设置中配置 API Key</span>}
            {status === "failed" && error && (
              <span className="text-sm" style={{ color: "var(--error)" }}>{error}</span>
            )}
          </div>
          <div className="flex gap-3 mt-4">
            <button className="btn btn-primary" onClick={() => navigate("/chat")}>
              开始对话
            </button>
            <button className="btn btn-ghost" onClick={() => navigate("/settings")}>
              打开设置
            </button>
          </div>
        </div>

        <LLMMetricsPanel />
      </div>

      <div className="card mb-4">
        <div className="card-title">快捷操作</div>
        <div className="quick-actions">
          <button className="quick-action" onClick={() => navigate("/chat")}>
            <ChatIcon />
            <span>开始对话</span>
          </button>
          <button className="quick-action" onClick={() => navigate("/skills")}>
            <SkillsIcon />
            <span>运行 Skill</span>
          </button>
          <button className="quick-action" onClick={() => navigate("/settings")}>
            <KeyIcon />
            <span>配置 API Key</span>
          </button>
          {!isReady ? (
            <RestartButton restart={restart} showToast={showToast} />
          ) : (
            <button className="quick-action" onClick={() => navigate("/settings")}>
              <UpdateIcon />
              <span>检查更新</span>
            </button>
          )}
        </div>
      </div>

      <DeviceCapsPanel />
    </div>
  );
}

function RestartButton({
  restart,
  showToast,
}: {
  restart: () => Promise<void>;
  showToast: (message: string, type?: "info" | "success" | "warning" | "error") => void;
}) {
  const [busy, setBusy] = useState(false);

  const handleClick = async () => {
    setBusy(true);
    try {
      await restart();
      showToast("后端重启中...", "info");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`重启失败: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button className="quick-action" onClick={handleClick} disabled={busy} aria-busy={busy} title="重新启动 GBT 后端">
      <ReloadIcon />
      <span>{busy ? "重启中..." : "重启后端"}</span>
    </button>
  );
}

function ChatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function SkillsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
    </svg>
  );
}

function KeyIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
    </svg>
  );
}

function ReloadIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}

function UpdateIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      <path d="M12 16l4-4m0 0l-4-4m4 4H8" />
    </svg>
  );
}
