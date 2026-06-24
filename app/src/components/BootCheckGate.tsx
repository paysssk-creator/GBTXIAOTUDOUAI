import { useEffect } from "react";
import { useBackend } from "../providers/BackendProvider";

export function BootCheckGate({ children }: { children: React.ReactNode }) {
  const { status, error, start } = useBackend();

  useEffect(() => {
    if (status === "idle") {
      start();
    }
  }, [status, start]);

  if (status === "healthy") {
    return <>{children}</>;
  }

  return (
    <div className="boot-screen">
      <div className="boot-card">
        <div className="spinner" />
        <h1 className="boot-title">GBT AI Workstation</h1>
        <p className="boot-message">
          {status === "starting" && "正在启动 GBT 后端..."}
          {status === "failed" && (error || "后端启动失败")}
          {status === "idle" && "准备启动..."}
        </p>
        {status === "failed" && (
          <button className="btn btn-primary" onClick={start}>
            重试
          </button>
        )}
      </div>
    </div>
  );
}
