import { ShieldCheck, CheckCircle, AlertTriangle, XCircle, Activity, GitBranch, Code } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import { auditReport } from "@/data/mockData";

export default function AuditReport() {
  const total = auditReport.summary.passed + auditReport.summary.warnings + auditReport.summary.failed;
  const rate = Math.round((auditReport.summary.passed / total) * 100);
  const icons = [GitBranch, GitBranch, GitBranch, Code, Code, Code, Code];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />审计报告
            </h1>
            <p className="font-mono text-sm text-muted-foreground mt-0.5">
              {new Date(auditReport.timestamp).toLocaleString("zh-CN")} · v12 地毯式审计 (10维度)
            </p>
          </div>
          <div className="text-right">
            <div className="font-mono text-4xl font-bold text-gain">{rate}%</div>
            <div className="text-xs text-muted-foreground">通过率</div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: CheckCircle, label: "通过", count: auditReport.summary.passed, cls: "text-gain bg-gain/10 border-gain/20" },
            { icon: AlertTriangle, label: "警告", count: auditReport.summary.warnings, cls: "text-warning bg-warning/10 border-warning/20" },
            { icon: XCircle, label: "失败", count: auditReport.summary.failed, cls: "text-muted-foreground bg-card border-border" },
          ].map(({ icon: Icon, label, count, cls }) => (
            <div key={label} className={`rounded-xl border p-5 ${cls}`}>
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-4 h-4" />
                <span className="text-xs font-semibold uppercase tracking-widest opacity-80">{label}</span>
              </div>
              <div className="font-mono text-4xl font-bold">{count}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Passed */}
          <div className="rounded-xl bg-card border border-border overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-gain" />
              <span className="text-sm font-semibold text-foreground">通过项目</span>
              <span className="ml-auto font-mono text-xs text-gain">{auditReport.passed.length} 项</span>
            </div>
            <div className="divide-y divide-border">
              {auditReport.passed.map((item, i) => {
                const Icon = icons[i] || Code;
                return (
                  <div key={i} className="flex items-center gap-3 px-5 py-3">
                    <Icon className="w-3.5 h-3.5 text-gain shrink-0" />
                    <span className="text-sm text-foreground flex-1">{item}</span>
                    <CheckCircle className="w-3.5 h-3.5 text-gain shrink-0" />
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-4">
            {/* Warnings */}
            <div className="rounded-xl bg-card border border-border overflow-hidden">
              <div className="px-5 py-4 border-b border-border flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-warning" />
                <span className="text-sm font-semibold text-foreground">警告项目</span>
                <span className="ml-auto font-mono text-xs text-warning">{auditReport.warnings.length} 项</span>
              </div>
              <div className="divide-y divide-border">
                {auditReport.warnings.map((w, i) => (
                  <div key={i} className="px-5 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-warning shrink-0" />
                      <span className="text-sm font-medium text-foreground">{w.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground pl-5">{w.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* V12 details */}
            <div className="rounded-xl bg-card border border-border overflow-hidden">
              <div className="px-5 py-4 border-b border-border flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" />
                <span className="text-sm font-semibold text-foreground">v12 详细维度</span>
              </div>
              <div className="p-5 space-y-3">
                {[
                  { l: "编译检查", v: `${auditReport.v12.compile.passed}/${auditReport.v12.compile.total} 通过` },
                  { l: "类型安全", v: auditReport.v12.typeSafety },
                  { l: "API 端点", v: `${auditReport.v12.api.passed}/${auditReport.v12.api.total} 通过` },
                  { l: "路由检测", v: `${auditReport.v12.router.passed}/${auditReport.v12.router.total} 通过` },
                  { l: "运行时", v: auditReport.v12.runtime },
                  { l: "线程安全", v: auditReport.v12.threadSafety },
                  { l: "逻辑检查", v: auditReport.v12.logic },
                ].map(d => (
                  <div key={d.l} className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">{d.l}</span>
                    <span className="font-mono text-xs text-gain text-right">{d.v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
