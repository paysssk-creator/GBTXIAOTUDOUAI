import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../providers/ToastProvider";
import { useAppStore } from "../store";
import { postJSON } from "../lib/api";
import { openExternal } from "../lib/tauri";
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

export default function Welcome() {
  const navigate = useNavigate();
  const { lastProvider, setLastProvider } = useAppStore();
  const { showToast } = useToast();
  const [provider, setProvider] = useState(lastProvider);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const providerName = PROVIDER_OPTIONS.find((p) => p.id === provider)?.name;
  const signupUrl = PROVIDER_SIGNUP_URLS[provider];

  const start = async () => {
    setSaving(true);
    setError("");
    try {
      if (apiKey.trim()) {
        await postJSON("/api/config", { [provider]: apiKey.trim() });
        showToast("API Key 已保存", "success");
      }
      navigate("/home");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`保存失败: ${msg}`, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="boot-screen">
      <div className="boot-card">
        <h1 className="boot-title">GBT AI Workstation</h1>
        <p className="boot-message">
          选择模型厂商并输入 API Key，或跳过稍后配置。
        </p>
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
            placeholder="API Key（可选）"
            onSubmit={start}
          />
        </div>
        {error && <p className="text-sm mt-2" style={{ color: "var(--error)" }}>{error}</p>}
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
        <button className="btn btn-primary mt-3 w-full" onClick={start} disabled={saving} aria-busy={saving}>
          {saving ? "保存中..." : "进入 GBT"}
        </button>
        <button className="btn btn-ghost w-full" onClick={() => navigate("/home")}>
          跳过
        </button>
      </div>
    </div>
  );
}
