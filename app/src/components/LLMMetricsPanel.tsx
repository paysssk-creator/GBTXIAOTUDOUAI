import { useEffect, useState } from "react";
import { fetchData } from "../lib/api";

interface MetricsSnapshot {
  current?: { provider?: string; model?: string };
  totals?: {
    requests?: number;
    tokens_in?: number;
    tokens_out?: number;
    cost_rmb?: number;
    avg_latency_s?: number;
  };
}

interface Metrics {
  requests?: number;
  tokensIn?: number;
  tokensOut?: number;
  costRmb?: number;
  avgLatency?: number;
  model?: string;
}

export function LLMMetricsPanel() {
  const [metrics, setMetrics] = useState<Metrics>({});
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const result = await fetchData<MetricsSnapshot>("/api/metrics");
      setMetrics({
        requests: result.totals?.requests,
        tokensIn: result.totals?.tokens_in,
        tokensOut: result.totals?.tokens_out,
        costRmb: result.totals?.cost_rmb,
        avgLatency: result.totals?.avg_latency_s,
        model: result.current?.model,
      });
    } catch {
      setMetrics({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, []);

  const items = [
    { label: "累计请求", value: metrics.requests ?? "-" },
    { label: "输入 Token", value: metrics.tokensIn ?? "-" },
    { label: "输出 Token", value: metrics.tokensOut ?? "-" },
    { label: "预估费用", value: metrics.costRmb !== undefined ? `¥${metrics.costRmb.toFixed(4)}` : "-" },
  ];

  return (
    <div className="card">
      <div className="card-title">
        <span>LLM 使用指标</span>
        <span className="text-xs text-dim">{metrics.model || "模型未配置"}</span>
        <button className="btn btn-ghost btn-sm ml-auto" onClick={refresh} disabled={loading}>
          {loading ? "刷新中..." : "刷新"}
        </button>
      </div>
      <div className="grid grid-4">
        {items.map((item) => (
          <div key={item.label}>
            <div className="metric-value">{item.value}</div>
            <div className="metric-label">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
