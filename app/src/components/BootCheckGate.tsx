import { useEffect } from "react";
import { useBackend } from "../providers/BackendProvider";

export function BootCheckGate({ children }: { children: React.ReactNode }) {
  const { status, error, logs, safeMode, enterSafeMode, start } = useBackend();

  useEffect(() => {
    if (status === "idle") {
      start();
    }
  }, [status, start]);

  if (status === "healthy" || safeMode) {
    return <>{children}</>;
  }

  const showSkip = status === "failed";
  const showLogs = status === "failed" || status === "starting";

  return (
    <div className="boot-screen">
      <div className="boot-card" style={{ width: 560, maxWidth: "92%" }}>
        <div className="spinner" />
        <h1 className="boot-title">GBT AI Workstation</h1>
        <p className="boot-message">
          {status === "starting" && "正在启动 GBT 后端..."}
          {status === "failed" && (error || "后端启动失败")}
          {status === "idle" && "准备启动..."}
        </p>

        {showLogs && (
          <div className="logs mb-3" style={{ height: 180, textAlign: "left" }}>
            {logs.length === 0 ? (
              <span className="text-subtle">等待日志...</span>
            ) : (
              logs.join("\n")
            )}
          </div>
        )}

        <div className="flex gap-2" style={{ justifyContent: "center", flexWrap: "wrap" }}>
          {status === "failed" && (
            <button className="btn btn-primary" onClick={start}>
              重试启动
            </button>
          )}
          {showSkip && (
            <button
              className="btn btn-ghost"
              onClick={enterSafeMode}
              title="跳过启动检查，进入设置页排查问题"
            >
              进入设置
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
