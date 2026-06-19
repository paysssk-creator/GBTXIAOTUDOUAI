import { Bot, RefreshCw } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import AgentCard from "@/components/dashboard/AgentCard";
import { useAgents } from "@/hooks/useSupabaseData";

const logs = [
  { t: "15:42:33", a: "brain", msg: "策略评估完成 — 创业板指突破信号", c: "text-gain" },
  { t: "15:42:31", a: "watcher", msg: "守夜人扫描 #2847 — 0 异常", c: "text-foreground" },
  { t: "15:42:28", a: "scraper", msg: "行情数据更新: sh000001=3312.48", c: "text-muted-foreground" },
  { t: "15:42:25", a: "guard", msg: "安全扫描通过 — 系统状态正常", c: "text-gain" },
  { t: "15:42:20", a: "trader", msg: "风控检查: 贵州茅台冷却 120min 激活", c: "text-warning" },
  { t: "15:42:15", a: "brain", msg: "DeepSeek v3 响应 187ms — 正常", c: "text-foreground" },
  { t: "15:42:10", a: "ocr", msg: "屏幕截图分析完成 — 3 个区域识别", c: "text-muted-foreground" },
];

export default function AgentMonitor() {
  const { data: agents, loading } = useAgents();
  const online = agents.filter(a => a.status === "online").length;
  const idle = agents.filter(a => a.status === "idle").length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary" />Agent 监控
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">{online} 运行中 · {idle} 空闲 · {agents.length} 总计</p>
          </div>
          <button className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors border border-border rounded-lg px-3 py-2 hover:border-primary/30">
            <RefreshCw className="w-3 h-3" />刷新
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "运行中", count: online, cls: "text-gain bg-gain/10 border-gain/20" },
            { label: "空闲", count: idle, cls: "text-warning bg-warning/10 border-warning/20" },
            { label: "总 Agent", count: agents.length, cls: "text-foreground bg-card border-border" },
          ].map(s => (
            <div key={s.label} className={`rounded-xl p-4 border text-center ${s.cls}`}>
              <div className="font-mono text-3xl font-bold">{s.count}</div>
              <div className="text-[10px] tracking-widest uppercase mt-1 opacity-70">{s.label}</div>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="text-sm text-muted-foreground">加载中...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {agents.map((agent, i) => (
              <div key={agent.id} className="animate-slide-up" style={{ animationDelay: `${i * 50}ms`, animationFillMode: "both" }}>
                <AgentCard
                  name={agent.name}
                  role={agent.role}
                  status={agent.status as "online" | "idle" | "offline"}
                  tasks={agent.tasks}
                  lastActive={agent.last_active}
                  memory={agent.memory}
                  model={agent.model}
                />
              </div>
            ))}
          </div>
        )}

        <div className="rounded-xl bg-card border border-border overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">实时日志流</span>
          </div>
          <div className="p-4 space-y-1.5 max-h-48 overflow-auto" style={{ background: "hsl(var(--terminal-bg))" }}>
            {logs.map((log, i) => (
              <div key={i} className="flex items-baseline gap-2">
                <span className="font-mono text-xs text-muted-foreground shrink-0">{log.t}</span>
                <span className="font-mono text-xs text-primary shrink-0">[{log.a}]</span>
                <span className={`font-mono text-xs ${log.c}`}>{log.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
