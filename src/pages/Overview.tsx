import { Brain, Server, Key, Clock, TrendingUp, Shield, Cpu } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import StatusCard from "@/components/dashboard/StatusCard";
import SystemGauge from "@/components/dashboard/SystemGauge";
import { useSystemStatus, useMarketIndices, useAuditReport } from "@/hooks/useSupabaseData";
import { systemResources } from "@/data/mockData";
import { cn } from "@/lib/utils";

export default function Overview() {
  const { status } = useSystemStatus();
  const { data: indices } = useMarketIndices();
  const { report } = useAuditReport();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-foreground">系统总览</h1>
          <p className="text-sm text-muted-foreground mt-0.5">实时状态监控 · {new Date().toLocaleDateString("zh-CN")}</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard icon={Brain} title="当前模型" value={status?.llm ?? "—"} subtitle={status?.model ?? ""} glow />
          <StatusCard icon={Server} title="MCP 服务" value={status?.mcp_count ?? 0} subtitle="服务器在线" />
          <StatusCard icon={Key} title="API 密钥" value={`${status?.keys_available ?? 0}/${status?.keys_total ?? 0}`} subtitle="可用/总计" />
          <StatusCard icon={Clock} title="运行时长" value={status?.uptime ?? "—"} subtitle={status?.version ?? ""} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 rounded-xl bg-card border border-border overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />主要指数
              </h2>
              <span className="text-[10px] font-mono text-muted-foreground">实时行情</span>
            </div>
            <div className="divide-y divide-border">
              {indices.map((idx) => (
                <div key={idx.code} className="flex items-center justify-between px-5 py-3 hover:bg-surface-overlay transition-colors">
                  <div>
                    <div className="text-sm font-medium text-foreground">{idx.name}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{idx.code}</div>
                  </div>
                  <div className="text-right">
                    <div className={cn("font-mono text-sm font-semibold", idx.change_pct >= 0 ? "text-gain" : "text-loss")}>
                      {Number(idx.price).toFixed(2)}
                    </div>
                    <span className={cn("font-mono text-xs px-1.5 py-0.5 rounded", idx.change_pct >= 0 ? "text-gain bg-gain/10" : "text-loss bg-loss/10")}>
                      {idx.change_pct >= 0 ? "+" : ""}{Number(idx.change_pct).toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

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
                  <div className="font-mono text-2xl font-bold text-gain">{report?.passed_count ?? 0}</div>
                  <div className="text-[10px] text-gain/70 uppercase tracking-widest">通过</div>
                </div>
                <div className="rounded-lg bg-warning/10 border border-warning/20 py-3">
                  <div className="font-mono text-2xl font-bold text-warning">{report?.warnings_count ?? 0}</div>
                  <div className="text-[10px] text-warning/70 uppercase tracking-widest">警告</div>
                </div>
                <div className="rounded-lg bg-muted border border-border py-3">
                  <div className="font-mono text-2xl font-bold text-muted-foreground">{report?.failed_count ?? 0}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-widest">失败</div>
                </div>
              </div>
              {report?.v12_details && (
                <div className="space-y-2">
                  {[
                    { l: "编译", v: `${report.v12_details.compile?.passed ?? 0}/${report.v12_details.compile?.total ?? 0}` },
                    { l: "API", v: `${report.v12_details.api?.passed ?? 0}/${report.v12_details.api?.total ?? 0}` },
                    { l: "路由", v: `${report.v12_details.router?.passed ?? 0}/${report.v12_details.router?.total ?? 0}` },
                    { l: "运行时", v: report.v12_details.runtime ?? "—" },
                  ].map((d) => (
                    <div key={d.l} className="flex justify-between">
                      <span className="text-xs text-muted-foreground">{d.l}</span>
                      <span className="font-mono text-xs text-gain">{d.v}</span>
                    </div>
                  ))}
                </div>
              )}
              {report?.timestamp && (
                <div className="font-mono text-[10px] text-muted-foreground border-t border-border pt-3">
                  {new Date(report.timestamp).toLocaleString("zh-CN")}
                </div>
              )}
            </div>
          </div>
        </div>

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
