import { Bot, Activity, Clock, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  name: string; role: string;
  status: "online" | "idle" | "offline";
  tasks: number; lastActive: string; memory: string; model: string;
}

const cfg = {
  online: { label: "运行中", dot: "bg-gain", dotStyle: { color: "hsl(var(--gain))", boxShadow: "0 0 6px hsl(var(--gain))" }, badge: "text-gain bg-gain/10 border-gain/20" },
  idle:   { label: "空闲",   dot: "bg-warning animate-pulse-dot", dotStyle: { color: "hsl(var(--warning))", boxShadow: "0 0 6px hsl(var(--warning))" }, badge: "text-warning bg-warning/10 border-warning/20" },
  offline:{ label: "离线",   dot: "bg-muted-foreground", dotStyle: {}, badge: "text-muted-foreground bg-muted border-border" },
};

export default function AgentCard({ name, role, status, tasks, lastActive, memory, model }: Props) {
  const c = cfg[status];
  return (
    <div className="rounded-xl p-5 bg-card border border-border transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30"
      style={{ boxShadow: "0 2px 8px rgba(0,0,0,.3)" }}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/15 flex items-center justify-center">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">{name}</div>
            <div className="text-xs text-muted-foreground">{role}</div>
          </div>
        </div>
        <span className={cn("flex items-center gap-1.5 text-[10px] font-semibold px-2 py-1 rounded-full border", c.badge)}>
          <span className={cn("w-1.5 h-1.5 rounded-full", c.dot)} style={c.dotStyle} />
          {c.label}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-3">
        {[
          { icon: Activity, label: "任务", val: tasks },
          { icon: Clock, label: "最近", val: lastActive },
          { icon: Cpu, label: "内存", val: memory },
        ].map(({ icon: Icon, label, val }) => (
          <div key={label}>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground uppercase tracking-widest mb-0.5">
              <Icon className="w-3 h-3" />{label}
            </div>
            <div className="font-mono text-sm font-semibold text-foreground">{val}</div>
          </div>
        ))}
      </div>
      <div className="pt-3 border-t border-border flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest">模型</span>
        <span className="font-mono text-xs text-primary">{model}</span>
      </div>
    </div>
  );
}
