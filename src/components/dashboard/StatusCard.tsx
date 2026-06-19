import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  icon: LucideIcon;
  title: string;
  value: string | number;
  subtitle?: string;
  delta?: number;
  status?: "online" | "warning" | "offline";
  glow?: boolean;
}

export default function StatusCard({ icon: Icon, title, value, subtitle, delta, status = "online", glow }: Props) {
  const dot = {
    online: { cls: "bg-gain", style: { color: "hsl(var(--gain))", boxShadow: "0 0 6px hsl(var(--gain))" } },
    warning: { cls: "bg-warning animate-pulse-dot", style: { color: "hsl(var(--warning))", boxShadow: "0 0 6px hsl(var(--warning))" } },
    offline: { cls: "bg-muted-foreground", style: {} },
  }[status];

  return (
    <div
      className="rounded-xl p-5 bg-card transition-all duration-200 hover:-translate-y-0.5"
      style={{
        boxShadow: glow
          ? "0 0 0 1px rgba(245,158,11,.30), 0 0 20px rgba(245,158,11,.08), 0 2px 8px rgba(0,0,0,.4)"
          : "0 0 0 1px hsl(222 25% 18%), 0 2px 8px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-primary" />
          <span className="text-[10px] font-semibold tracking-widest uppercase text-muted-foreground">{title}</span>
        </div>
        <span className={cn("w-2 h-2 rounded-full shrink-0", dot.cls)} style={dot.style} />
      </div>
      <div className="font-mono text-2xl font-semibold text-foreground">{value}</div>
      {(subtitle || delta !== undefined) && (
        <div className="mt-1.5 flex items-center gap-1.5">
          {delta !== undefined && (
            <span className={cn("font-mono text-xs font-medium", delta > 0 ? "text-gain" : delta < 0 ? "text-loss" : "text-muted-foreground")}>
              {delta > 0 ? "▲" : delta < 0 ? "▼" : "—"} {Math.abs(delta).toFixed(2)}%
            </span>
          )}
          {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
