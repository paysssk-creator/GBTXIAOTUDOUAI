import { createPortal } from "react-dom";
import { useAppUpdate } from "../hooks/useAppUpdate";

export function AppUpdatePrompt() {
  const { phase, info, error, install, checkForUpdate, reset } =
    useAppUpdate({ autoCheck: true, autoDownload: true });

  if (phase === "idle" || phase === "checking" || phase === "available" || phase === "downloading") {
    return null;
  }

  return createPortal(
    <div className="update-prompt" role="status" aria-live="polite">
      <div className="update-prompt-header">
        <div className="update-prompt-title">
          <UpdateIcon />
          {phase === "ready_to_install" && "更新已准备好"}
          {phase === "installing" && "正在安装"}
          {phase === "restarting" && "正在重启"}
          {phase === "error" && "更新失败"}
        </div>
        {(phase === "ready_to_install" || phase === "error") && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={phase === "error" ? reset : () => {}}
            aria-label="关闭更新提示"
          >
            ✕
          </button>
        )}
      </div>
      <div className="update-prompt-body">
        {phase === "ready_to_install" && (
          <>
            <p>
              {info?.version
                ? `GBT ${info.version} 已下载完成，重启后即可使用。`
                : "新版本已下载完成，重启后即可使用。"}
            </p>
            <div className="update-prompt-actions">
              <button className="btn btn-primary" onClick={install}>
                立即重启
              </button>
              <button className="btn btn-ghost" onClick={() => {}}>
                稍后
              </button>
            </div>
          </>
        )}

        {(phase === "installing" || phase === "restarting") && (
          <>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: "100%" }} />
            </div>
            <p className="mt-2 text-xs text-dim">
              {phase === "installing" ? "正在安装更新..." : "正在重启应用..."}
            </p>
          </>
        )}

        {phase === "error" && (
          <>
            <p>{error || "更新检查失败，请稍后再试。"}</p>
            <div className="update-prompt-actions">
              <button className="btn btn-primary" onClick={checkForUpdate}>
                重试
              </button>
              <button className="btn btn-ghost" onClick={reset}>
                忽略
              </button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}

function UpdateIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path d="M10 2a8 8 0 015.292 13.97v1.78a.75.75 0 01-1.5 0v-1.06a.75.75 0 01.22-.53A6.5 6.5 0 1010 16.5a.75.75 0 010 1.5A8 8 0 1110 2z" />
      <path d="M9.25 6.75a.75.75 0 011.5 0v3.69l2.22 2.22a.75.75 0 11-1.06 1.06l-2.44-2.44a.75.75 0 01-.22-.53V6.75z" />
    </svg>
  );
}
