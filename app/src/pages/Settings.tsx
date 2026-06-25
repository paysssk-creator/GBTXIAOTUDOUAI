import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { check } from "@tauri-apps/plugin-updater";
import { useBackend } from "../providers/BackendProvider";
import { useAppStore } from "../store";
import { fetchData, postJSON } from "../lib/api";
import { isTauri } from "../lib/tauri";

const PROVIDER_OPTIONS = [
  { id: "OPENAI_API_KEY", name: "OpenAI (GPT-4o / GPT-5)" },
  { id: "ANTHROPIC_API_KEY", name: "Anthropic (Claude)" },
  { id: "GLM_API_KEY", name: "智谱 GLM" },
  { id: "GEMINI_API_KEY", name: "Google Gemini" },
  { id: "DEEPSEEK_API_KEY", name: "DeepSeek" },
  { id: "QWEN_API_KEY", name: "阿里 Qwen" },
  { id: "GROK_API_KEY", name: "xAI Grok" },
  { id: "MOONSHOT_API_KEY", name: "Kimi (Moonshot)" },
];

export default function Settings() {
  const { theme, setTheme } = useAppStore();
  const { status, logs, restart, stop } = useBackend();
  const [provider, setProvider] = useState(PROVIDER_OPTIONS[0].id);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [updateMessage, setUpdateMessage] = useState("");

  useEffect(() => {
    fetchData<{ api_key_set?: boolean }>("/api/status")
      .then((status) => {
        if (status.api_key_set) setMessage("API Key 已配置");
      })
      .catch(() => {});
  }, []);

  const saveApiKey = async () => {
    if (!apiKey.trim()) return;
    setSaving(true);
    try {
      await postJSON("/api/config", { [provider]: apiKey.trim() });
      setMessage("API Key 已保存，重启后生效");
      setApiKey("");
    } catch (err) {
      setMessage(`保存失败: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  const openDataDir = async () => {
    if (isTauri()) {
      await invoke("open_data_dir");
    }
  };

  const checkForUpdate = async () => {
    if (!isTauri()) {
      setUpdateMessage("当前环境不支持自动更新");
      return;
    }
    setUpdateMessage("正在检查更新...");
    try {
      const update = await check();
      setUpdateMessage(update ? `发现新版本 ${update.version}，重启后安装` : "当前已是最新版本");
    } catch (err) {
      setUpdateMessage(`检查失败: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">配置 GBT 后端、主题与账户</p>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">API Key</div>
          <select
            className="input"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            {PROVIDER_OPTIONS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <input
            className="input mt-2"
            type="password"
            placeholder={`输入你的 ${PROVIDER_OPTIONS.find((p) => p.id === provider)?.name} API Key`}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          {message && <p className="text-sm mt-2 text-dim">{message}</p>}
          <button className="btn btn-primary mt-3" onClick={saveApiKey} disabled={saving}>
            {saving ? "保存中..." : "保存 API Key"}
          </button>
        </div>

        <div className="card">
          <div className="card-title">外观</div>
          <div className="flex gap-2">
            {(["light", "dark", "system"] as const).map((m) => (
              <button
                key={m}
                className={`btn ${theme === m ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setTheme(m)}
              >
                {m === "light" ? "浅色" : m === "dark" ? "深色" : "跟随系统"}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title">后端</div>
          <p className="text-sm text-dim mb-3">状态: {status}</p>
          <div className="flex gap-2">
            <button className="btn btn-ghost" onClick={restart}>
              重启后端
            </button>
            <button className="btn btn-ghost" onClick={stop}>
              停止后端
            </button>
            <button className="btn btn-ghost" onClick={openDataDir}>
              打开数据目录
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-title">更新</div>
          <p className="text-sm text-dim mb-3">{updateMessage || "自动更新会在启动时静默检查"}</p>
          <button className="btn btn-ghost" onClick={checkForUpdate}>
            检查更新
          </button>
        </div>

        <div className="card">
          <div className="card-title flex justify-between items-center">
            <span>后端日志</span>
            <div className="flex gap-2">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => navigator.clipboard.writeText(logs.join("\n"))}
                disabled={logs.length === 0}
              >
                复制
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => useAppStore.getState().setBackendInfo({ logs: [] })}
                disabled={logs.length === 0}
              >
                清空
              </button>
            </div>
          </div>
          <LogViewer logs={logs} />
        </div>
      </div>
    </div>
  );
}

function LogViewer({ logs }: { logs: string[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={ref} className="logs">
      {logs.length === 0 ? (
        <span className="text-subtle">暂无日志</span>
      ) : (
        logs.join("\n")
      )}
    </div>
  );
}
