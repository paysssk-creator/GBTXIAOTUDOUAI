import { useEffect, useMemo, useRef, useState } from "react";
import { useToast } from "../providers/ToastProvider";
import { useSkills, type SkillResult } from "../hooks/useSkills";

interface SkillRun {
  id: number;
  name: string;
  description: string;
  text: string;
  result: SkillResult;
  time: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  all: "全部",
  desktop: "桌面控制",
  trading: "交易",
  system: "系统",
  notification: "通知",
  hacker: "工具",
};

function formatJson(value: unknown): string {
  if (value === undefined || value === null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function ClearIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function resultText(run: SkillRun): string {
  const parts: string[] = [];
  if (run.text) parts.push(`输入: ${run.text}`);
  if (run.result.message) parts.push(run.result.message);
  if (run.result.error) parts.push(`错误: ${run.result.error}`);
  if (run.result.data !== undefined && run.result.data !== null) {
    parts.push(formatJson(run.result.data));
  }
  return parts.join("\n\n");
}

export default function Skills() {
  const { skills, loading, invokeSkill } = useSkills();
  const { showToast } = useToast();
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [running, setRunning] = useState<string | null>(null);
  const [history, setHistory] = useState<SkillRun[]>([]);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const s of skills) {
      if (s.category) set.add(s.category);
    }
    return ["all", ...Array.from(set)];
  }, [skills]);

  const filtered = skills.filter((s) => {
    const matchesQuery =
      s.name.toLowerCase().includes(query.toLowerCase()) ||
      (s.description && s.description.toLowerCase().includes(query.toLowerCase()));
    const matchesCategory = category === "all" || s.category === category;
    return matchesQuery && matchesCategory;
  });

  const handleInvoke = async (skill: { name: string; description: string }) => {
    setRunning(skill.name);
    const res = await invokeSkill(skill.name, input.trim());
    setRunning(null);
    setHistory((prev) => [
      {
        id: Date.now(),
        name: skill.name,
        description: skill.description,
        text: input.trim(),
        result: res,
        time: new Date().toLocaleTimeString(),
      },
      ...prev.slice(0, 9),
    ]);
    if (res.ok) {
      showToast(`${skill.description || skill.name} 执行成功`, "success");
    } else {
      showToast(`${skill.description || skill.name} 执行失败`, "error");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Skills</h1>
        <p className="page-subtitle">GBT 内置 {skills.length} 个技能插件</p>
      </div>

      <div className="grid grid-2 mb-4">
        <div className="card">
          <div className="card-title">技能指令</div>
          <input
            className="input"
            placeholder="输入要传给技能的文本或参数，例如：600519、https://example.com、查询内容"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <p className="text-xs text-dim mt-2">
            留空则执行默认行为。点击下方任意 skill 时会传入这段文本。
          </p>
        </div>
        <div className="card">
          <div className="card-title">搜索技能</div>
          <div className="password-input-wrap">
            <input
              ref={searchRef}
              className="input"
              placeholder="按名称或描述过滤..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button
                type="button"
                className="password-toggle"
                onClick={() => setQuery("")}
                aria-label="清空搜索"
                tabIndex={-1}
              >
                <ClearIcon />
              </button>
            )}
          </div>
          <p className="text-xs text-dim mt-2">
            共 {skills.length} 个技能，当前显示 {filtered.length} 个
          </p>
        </div>
      </div>

      <div className="skill-category-tabs mb-4">
        {categories.map((c) => (
          <button
            key={c}
            className={`skill-category-tab ${category === c ? "active" : ""}`}
            onClick={() => setCategory(c)}
            aria-pressed={category === c}
          >
            {CATEGORY_LABELS[c] || c}
          </button>
        ))}
      </div>

      <div className="grid grid-3">
        {filtered.map((skill) => (
          <div key={skill.name} className="card">
            <div className="card-title">
              {skill.description || skill.name}
              {skill.category && (
                <span className="skill-category-badge">{CATEGORY_LABELS[skill.category] || skill.category}</span>
              )}
            </div>
            <p className="text-sm text-dim mb-3">{skill.name}</p>
            <button
              className="btn btn-primary btn-sm w-full"
              onClick={() => handleInvoke(skill)}
              disabled={running !== null}
              aria-busy={running === skill.name}
            >
              {running === skill.name ? "执行中..." : "执行"}
            </button>
          </div>
        ))}
        {loading && <p className="text-dim">加载中...</p>}
        {!loading && filtered.length === 0 && <p className="text-dim">没有找到匹配的技能</p>}
      </div>

      {history.length > 0 && (
        <div className="mt-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="page-subtitle" style={{ marginTop: 0 }}>执行结果</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => setHistory([])}>
              清空
            </button>
          </div>
          <div className="skill-results">
            {history.map((run) => (
              <div key={run.id} className={`skill-result ${run.result.ok ? "success" : "error"}`}>
                <div className="skill-result-header">
                  <div className="skill-result-title">
                    <span className="skill-result-dot" />
                    {run.description || run.name}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-subtle">{run.time}</span>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(resultText(run));
                          showToast("已复制结果", "success");
                        } catch {
                          showToast("复制失败", "error");
                        }
                      }}
                      aria-label="复制结果"
                    >
                      复制
                    </button>
                  </div>
                </div>
                {run.text && <p className="skill-result-message">输入: {run.text}</p>}
                {run.result.message && <p className="skill-result-message">{run.result.message}</p>}
                {run.result.error && <p className="skill-result-error">{run.result.error}</p>}
                {run.result.data !== undefined && run.result.data !== null && (
                  <pre className="skill-result-data">{formatJson(run.result.data)}</pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
