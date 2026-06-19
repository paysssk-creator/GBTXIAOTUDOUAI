import { Brain, Server, Key, Clock, TrendingUp, Shield, Cpu } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import StatusCard from "@/components/dashboard/StatusCard";
import SystemGauge from "@/components/dashboard/SystemGauge";
import { systemStatus, systemResources, auditReport, marketIndices } from "@/data/mockData";
import { cn } from "@/lib/utils";

export default function Overview() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-foreground">系统总览</h1>
          <p className="text-sm text-muted-foreground mt-0.5">实时状态监控 · {new Date().toLocaleDateString("zh-CN")}</p>
        </div>

        {/* Status cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard icon={Brain} title="当前模型" value={systemStatus.llm} subtitle={systemStatus.model} glow />
          <StatusCard icon={Server} title="MCP 服务" value={systemStatus.mcpCount} subtitle="服务器在线" />
          <StatusCard icon={Key} title="API 密钥" value={`${systemStatus.keysAvailable}/${systemStatus.keysTotal}`} subtitle="可用/总计" />
          <StatusCard icon={Clock} title="运行时长" value={systemStatus.uptime} subtitle={systemStatus.version} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Market */}
          <div className="lg:col-span-2 rounded-xl bg-card border border-border overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />主要指数
              </h2>
              <span className="text-[10px] font-mono text-muted-foreground">实时行情</span>
            </div>
            <div className="divide-y divide-border">
              {marketIndices.map((idx) => (
                <div key={idx.code} className="flex items-center justify-between px-5 py-3 hover:bg-surface-overlay transition-colors">
                  <div>
                    <div className="text-sm font-medium text-foreground">{idx.name}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{idx.code}</div>
                  </div>
                  <div className="text-right">
                    <div className={cn("font-mono text-sm font-semibold", idx.changePct >= 0 ? "text-gain" : "text-loss")}>
                      {idx.price.toFixed(2)}
                    </div>
                    <span className={cn("font-mono text-xs px-1.5 py-0.5 rounded", idx.changePct >= 0 ? "text-gain bg-gain/10" : "text-loss bg-loss/10")}>
                      {idx.changePct >= 0 ? "+" : ""}{idx.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Audit summary */}
          <div className="rounded-xl bg-card border border-border overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />审计摘要
              </h2>
              <span className="text-[10px] font-mono text-muted-foreground">v12</span>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-gain/10 border border-gain/20 py-3">
                  <div className="font-mono text-2xl font-bold text-gain">{auditReport.summary.passed}</div>
                  <div className="text-[10px] text-gain/70 uppercase tracking-widest">通过</div>
                </div>
                <div className="rounded-lg bg-warning/10 border border-warning/20 py-3">
                  <div className="font-mono text-2xl font-bold text-warning">{auditReport.summary.warnings}</div>
                  <div className="text-[10px] text-warning/70 uppercase tracking-widest">警告</div>
                </div>
                <div className="rounded-lg bg-muted border border-border py-3">
                  <div className="font-mono text-2xl font-bold text-muted-foreground">{auditReport.summary.failed}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-widest">失败</div>
                </div>
              </div>
              <div className="space-y-2">
                {[
                  { l: "编译", v: `${auditReport.v12.compile.passed}/${auditReport.v12.compile.total}` },
                  { l: "API", v: `${auditReport.v12.api.passed}/${auditReport.v12.api.total}` },
                  { l: "路由", v: `${auditReport.v12.router.passed}/${auditReport.v12.router.total}` },
                  { l: "运行时", v: "全绿" },
                ].map((d) => (
                  <div key={d.l} className="flex justify-between">
                    <span className="text-xs text-muted-foreground">{d.l}</span>
                    <span className="font-mono text-xs text-gain">{d.v}</span>
                  </div>
                ))}
              </div>
              <div className="font-mono text-[10px] text-muted-foreground border-t border-border pt-3">
                {new Date(auditReport.timestamp).toLocaleString("zh-CN")}
              </div>
            </div>
          </div>
        </div>

        {/* System resources */}
        <div>
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-primary" />系统资源
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <SystemGauge label="CPU" value={systemResources.cpu} detail="Intel i9-13900K" />
            <SystemGauge label="内存" value={systemResources.memory} detail={`${systemResources.memoryUsedGB}/${systemResources.memoryTotalGB} GB`} />
            <SystemGauge label="GPU" value={systemResources.gpu} detail="RTX 4090" />
            <SystemGauge label="网络" value={systemResources.network} detail="上传带宽" />
          </div>
        </div>
      </div>
    </div>
  );
}
