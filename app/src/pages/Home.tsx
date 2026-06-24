import { useNavigate } from "react-router-dom";
import { useBackend } from "../providers/BackendProvider";
import { useCoreState } from "../providers/CoreStateProvider";
import { DeviceCapsPanel } from "../components/DeviceCapsPanel";
import { LLMMetricsPanel } from "../components/LLMMetricsPanel";

export default function Home() {
  const navigate = useNavigate();
  const { status } = useBackend();
  const { apiKeySet, model } = useCoreState();

  const isReady = status === "healthy";

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">欢迎回来</h1>
        <p className="page-subtitle">
          {isReady ? "GBT 后端运行正常" : "GBT 后端未就绪"}
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

      <DeviceCapsPanel />
    </div>
  );
}
