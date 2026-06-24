import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postJSON } from "../lib/api";

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

export default function Welcome() {
  const navigate = useNavigate();
  const [provider, setProvider] = useState(PROVIDER_OPTIONS[0].id);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const start = async () => {
    setSaving(true);
    setError("");
    try {
      if (apiKey.trim()) {
        await postJSON("/api/config", { [provider]: apiKey.trim() });
      }
      navigate("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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
          onChange={(e) => setProvider(e.target.value)}
        >
          {PROVIDER_OPTIONS.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <input
          className="input mt-2"
          type="password"
          placeholder="API Key（可选）"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        {error && <p className="text-sm mt-2" style={{ color: "var(--error)" }}>{error}</p>}
        <button className="btn btn-primary mt-3 w-full" onClick={start} disabled={saving}>
          {saving ? "保存中..." : "进入 GBT"}
        </button>
        <button className="btn btn-ghost w-full" onClick={() => navigate("/home")}>
          跳过
        </button>
      </div>
    </div>
  );
}
