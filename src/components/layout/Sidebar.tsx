import { NavLink } from "react-router-dom";
import { LayoutDashboard, Bot, BarChart2, ShieldCheck, MessageSquare, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "总览", icon: LayoutDashboard, end: true },
  { to: "/agents", label: "Agent 监控", icon: Bot },
  { to: "/market", label: "市场行情", icon: BarChart2 },
  { to: "/audit", label: "审计报告", icon: ShieldCheck },
  { to: "/chat", label: "AI 对话", icon: MessageSquare },
];

export default function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 w-60 flex flex-col border-r border-border bg-surface-base z-50">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center">
          <Zap className="w-4 h-4 text-primary" />
        </div>
        <div>
          <div className="font-extrabold text-base leading-none">
            <span className="text-primary">GBT</span>
            <span className="text-foreground"> Pro</span>
          </div>
          <div className="text-[10px] text-muted-foreground tracking-widest uppercase mt-0.5">
            AI Trading Terminal
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-auto">
        <p className="text-[10px] text-muted-foreground tracking-widest uppercase px-3 pb-2">导航</p>
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => cn(
              "relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-primary/5"
            )}>
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r-full" />}
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Status footer */}
      <div className="px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-gain animate-pulse-dot" style={{ color: "hsl(var(--gain))" }} />
          <span className="font-mono text-xs text-muted-foreground">v2.1.0619 · 运行中</span>
        </div>
      </div>
    </aside>
  );
}
