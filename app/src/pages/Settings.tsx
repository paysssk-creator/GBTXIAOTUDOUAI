import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { relaunch } from "@tauri-apps/plugin-process";
import { useBackend } from "../providers/BackendProvider";
import { useToast } from "../providers/ToastProvider";
import { useAppStore } from "../store";
import { fetchData, postJSON } from "../lib/api";
import { isTauri, openExternal } from "../lib/tauri";
import { PasswordInput } from "../components/PasswordInput";

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

const PROVIDER_SIGNUP_URLS: Record<string, string> = {
  OPENAI_API_KEY: "https://platform.openai.com/signup",
  ANTHROPIC_API_KEY: "https://console.anthropic.com/settings/keys",
  GLM_API_KEY: "https://open.bigmodel.cn/usercenter/apikeys",
  GEMINI_API_KEY: "https://aistudio.google.com/app/apikey",
  DEEPSEEK_API_KEY: "https://platform.deepseek.com/api_keys",
  QWEN_API_KEY: "https://bailian.console.aliyun.com/?apiKey=1#/api-key",
  GROK_API_KEY: "https://console.x.ai/team/default/api-keys",
  MOONSHOT_API_KEY: "https://platform.moonshot.cn/console/api-keys",
};

export default function Settings() {
  const { theme, setTheme, lastProvider, setLastProvider } = useAppStore();
  const { status, logs, restart, stop, clearLogs } = useBackend();
  const { showToast } = useToast();
  const [provider, setProvider] = useState(lastProvider);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [updateMessage, setUpdateMessage] = useState("");
  const [updateInfo, setUpdateInfo] = useState<{ version: string; body?: string } | null>(null);
  const [installing, setInstalling] = useState(false);
  const [autoAuthorize, setAutoAuthorize] = useState(false);
  const [autoAuthorizeLoading, setAutoAuthorizeLoading] = useState(false);

  const providerName = PROVIDER_OPTIONS.find((p) => p.id === provider)?.name;
  const signupUrl = PROVIDER_SIGNUP_URLS[provider];
  const version = useAppStore((state) => state.profile.version);
  const dataDir = useAppStore((state) => state.backend.dataDir);

  useEffect(() => {
    fetchData<{ api_key_set?: boolean }>("/api/status")
      .then((status) => {
        if (status.api_key_set) setMessage("API Key 已配置");
      })
      .catch(() => {});
    fetchData<{ auto_authorize?: boolean }>("/api/trade/auto_authorize")
      .then((data) => {
        if (typeof data.auto_authorize === "boolean") setAutoAuthorize(data.auto_authorize);
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
      showToast("API Key 已保存", "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessage(`保存失败: ${msg}`);
      showToast(`保存失败: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const openDataDir = async () => {
    if (!isTauri()) {
      showToast("当前环境不支持打开目录", "warning");
      return;
    }
    try {
      await invoke("open_data_dir");
      showToast("已打开数据目录", "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`打开失败: ${msg}`, "error");
    }
  };

  const handleRestart = async () => {
    try {
      await restart();
      showToast("后端重启中...", "info");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`重启失败: ${msg}`, "error");
    }
  };

  const handleStop = async () => {
    if (!window.confirm("确定要停止 GBT 后端吗？停止后将无法使用对话和 Skills。")) {
      return;
    }
    try {
      await stop();
      showToast("后端已停止", "info");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`停止失败: ${msg}`, "error");
    }
  };

  const checkForUpdate = async () => {
    if (!isTauri()) {
      setUpdateMessage("当前环境不支持自动更新");
      showToast("当前环境不支持自动更新", "warning");
      return;
    }
    setUpdateMessage("正在检查更新...");
    setUpdateInfo(null);
    try {
      const update = await invoke<{ version: string; body?: string } | null>("check_update");
      if (update) {
        setUpdateInfo(update);
        setUpdateMessage(`发现新版本 ${update.version}`);
        showToast(`发现新版本 ${update.version}`, "success");
      } else {
        setUpdateMessage("当前已是最新版本");
        showToast("当前已是最新版本", "info");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setUpdateMessage(`检查失败: ${msg}`);
      showToast(`检查失败: ${msg}`, "error");
    }
  };

  const installUpdate = async () => {
    if (!isTauri()) return;
    setInstalling(true);
    setUpdateMessage("正在下载并安装更新...");
    try {
      await invoke("install_update");
      setUpdateMessage("安装完成，即将重启");
      showToast("安装完成，即将重启", "success");
      await relaunch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setUpdateMessage(`安装失败: ${msg}`);
      showToast(`安装失败: ${msg}`, "error");
      setInstalling(false);
    }
  };

  const toggleAutoAuthorize = async () => {
    const next = !autoAuthorize;
    if (next && !window.confirm("开启自动授权后，AI 将直接执行交易和桌面操控，不再询问确认。\n\n若连接的是真实券商账户，可能造成真实资金损失。确定开启吗？")) {
      return;
    }
    setAutoAuthorizeLoading(true);
    try {
      await postJSON("/api/trade/auto_authorize", { enabled: next });
      setAutoAuthorize(next);
      showToast(next ? "自动授权已开启" : "自动授权已关闭", next ? "warning" : "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`切换失败: ${msg}`, "error");
    } finally {
      setAutoAuthorizeLoading(false);
    }
  };

  const copyLogs = async () => {
    if (logs.length === 0) return;
    try {
      await navigator.clipboard.writeText(logs.join("\n"));
      showToast("日志已复制", "success");
    } catch {
      showToast("复制失败", "error");
    }
  };

  const handleClearLogs = () => {
    clearLogs();
    showToast("日志已清空", "info");
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">配置 GBT 后端、主题与账户</p>
      </div>

      <div className="grid grid-2">
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            saveApiKey();
          }}
        >
          <div className="card-title">API Key</div>
          <select
            className="input"
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
              setLastProvider(e.target.value);
            }}
          >
            {PROVIDER_OPTIONS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <div className="mt-2">
            <PasswordInput
              value={apiKey}
              onChange={setApiKey}
              placeholder={`输入你的 ${providerName} API Key`}
              onSubmit={saveApiKey}
            />
          </div>
          {signupUrl && (
            <button
              type="button"
              className="btn btn-ghost btn-sm w-full mt-2"
              onClick={() =>
                openExternal(signupUrl).catch((err) =>
                  showToast(`打开链接失败: ${err instanceof Error ? err.message : String(err)}`, "error")
                )
              }
            >
              还没有 {providerName} API Key？去官网注册
            </button>
          )}
          {message && <p className="text-sm mt-2 text-dim">{message}</p>}
          <button type="submit" className="btn btn-primary mt-3" disabled={saving} aria-busy={saving}>
            {saving ? "保存中..." : "保存 API Key"}
          </button>
        </form>

        <div className="card">
          <div className="card-title">外观</div>
          <div className="flex gap-2">
            {(["light", "dark", "system"] as const).map((m) => (
              <button
                key={m}
                className={`btn ${theme === m ? "btn-primary" : "btn-ghost"}`}
                onClick={() => {
                  setTheme(m);
                  showToast(m === "light" ? "已切换浅色主题" : m === "dark" ? "已切换深色主题" : "已跟随系统主题", "success");
                }}
                aria-pressed={theme === m}
              >
                {m === "light" ? "浅色" : m === "dark" ? "深色" : "跟随系统"}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title">后端</div>
          <p className="text-sm text-dim mb-1">状态: {status}</p>
          {version && <p className="text-sm text-dim mb-1">版本: {version}</p>}
          {dataDir && (
            <p className="text-sm text-dim mb-3" style={{ wordBreak: "break-all" }}>
              数据目录: {dataDir}
            </p>
          )}
          {!dataDir && <div className="mb-3" />}
          <div className="flex gap-2">
            <button className="btn btn-ghost" onClick={handleRestart}>
              重启后端
            </button>
            <button className="btn btn-ghost" onClick={handleStop}>
              停止后端
            </button>
            <button className="btn btn-ghost" onClick={openDataDir}>
              打开数据目录
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-title">自动授权</div>
          <p className="text-sm text-dim mb-3">
            开启后 AI 执行交易和桌面操控时不再进入模拟模式。
            <span style={{ color: "var(--error)" }}>涉及真实资金账户时请务必谨慎。</span>
          </p>
          <button
            className={`btn ${autoAuthorize ? "btn-primary" : "btn-ghost"}`}
            onClick={toggleAutoAuthorize}
            disabled={autoAuthorizeLoading}
            aria-busy={autoAuthorizeLoading}
          >
            {autoAuthorizeLoading ? "切换中..." : autoAuthorize ? "自动授权：已开启" : "自动授权：已关闭"}
          </button>
        </div>

        <div className="card">
          <div className="card-title">更新</div>
          <p className="text-sm text-dim mb-3">{updateMessage || "自动更新会在启动时静默检查"}</p>
          {updateInfo?.body && (
            <pre className="text-xs text-dim mb-3" style={{ maxHeight: 120, overflow: "auto", whiteSpace: "pre-wrap" }}>
              {updateInfo.body}
            </pre>
          )}
          <div className="flex gap-2">
            <button className="btn btn-ghost" onClick={checkForUpdate} disabled={installing} aria-busy={installing}>
              检查更新
            </button>
            {updateInfo && (
              <button className="btn btn-primary" onClick={installUpdate} disabled={installing} aria-busy={installing}>
                {installing ? "安装中..." : `安装 ${updateInfo.version}`}
              </button>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-title flex justify-between items-center">
            <span>后端日志</span>
            <div className="flex gap-2">
              <button
                className="btn btn-ghost btn-sm"
                onClick={copyLogs}
                disabled={logs.length === 0}
              >
                复制
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleClearLogs}
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
