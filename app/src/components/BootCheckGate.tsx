import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBackend } from "../providers/BackendProvider";

export function BootCheckGate({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { status, error, logs, safeMode, enterSafeMode, start } = useBackend();
  const [showLogs, setShowLogs] = useState(false);

  const handleEnterSafeMode = () => {
    enterSafeMode();
    navigate("/settings", { replace: true });
  };

  useEffect(() => {
    if (status === "idle") {
      start();
    }
  }, [status, start]);

  if (status === "healthy" || safeMode) {
    return <>{children}</>;
  }

  const showSkip = status === "failed";
  const displayLogs = showLogs || status === "starting";

  return (
    <div className="boot-screen">
      <div className="boot-card" style={{ width: 600, maxWidth: "94%" }}>
        <div className="spinner" />
        <h1 className="boot-title">GBT AI Workstation</h1>
        <p className="boot-message">
          {status === "starting" && "正在启动 GBT 后端并执行健康检查..."}
          {status === "failed" && (error || "后端启动失败")}
          {status === "idle" && "准备启动..."}
        </p>

        {status === "starting" && logs.length > 0 && (
          <p className="text-xs text-dim mb-2">
            已尝试 {logs.filter((l) => l.startsWith("[Health]")).length} 次健康检查
          </p>
        )}

        {displayLogs && (
          <div className="logs mb-3" style={{ height: 200, textAlign: "left" }}>
            {logs.length === 0 ? (
              <span className="text-subtle">等待日志...</span>
            ) : (
              logs.join("\n")
            )}
          </div>
        )}

        <div className="boot-actions">
          {status === "failed" && (
            <button className="btn btn-primary" onClick={start}>
              重试启动
            </button>
          )}
          {logs.length > 0 && (
            <button className="btn btn-ghost" onClick={() => setShowLogs((v) => !v)}>
              {showLogs ? "隐藏日志" : "查看日志"}
            </button>
          )}
          {showSkip && (
            <button
              className="btn btn-ghost"
              onClick={handleEnterSafeMode}
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
