import { useState } from "react";
import { useSkills } from "../hooks/useSkills";

export default function Skills() {
  const { skills, loading, invokeSkill } = useSkills();
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<{ name: string; text: string } | null>(null);

  const handleInvoke = async (skill: { name: string; description: string }) => {
    setRunning(skill.name);
    setResult({ name: skill.name, text: "执行中..." });
    const res = await invokeSkill(skill.name);
    setRunning(null);
    setResult({
      name: skill.name,
      text: res.ok ? `✓ ${skill.description} 执行成功` : `✗ 失败: ${res.error}`,
    });
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Skills</h1>
        <p className="page-subtitle">GBT 内置 {skills.length} 个技能插件</p>
      </div>

      <div className="grid grid-3">
        {skills.map((skill) => (
          <div key={skill.name} className="card">
            <div className="card-title">{skill.description || skill.name}</div>
            <p className="text-sm text-dim mb-3">{skill.name}</p>
            <button
              className="btn btn-primary btn-sm w-full"
              onClick={() => handleInvoke(skill)}
              disabled={running === skill.name}
            >
              {running === skill.name ? "执行中..." : "执行"}
            </button>
          </div>
        ))}
        {loading && <p className="text-dim">加载中...</p>}
      </div>

      {result && (
        <div className="card mt-4">
          <div className="card-title">执行结果</div>
          <p className="text-sm" style={{ color: result.text.startsWith("✓") ? "var(--success)" : "var(--error)" }}>
            {result.text}
          </p>
        </div>
      )}
    </div>
  );
}
