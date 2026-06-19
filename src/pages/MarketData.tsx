import { BarChart2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import { marketIndices } from "@/data/mockData";
import { cn } from "@/lib/utils";

export default function MarketData() {
  const gainers = marketIndices.filter(i => i.changePct > 0).length;
  const losers = marketIndices.filter(i => i.changePct < 0).length;
  const flat = marketIndices.filter(i => i.changePct === 0).length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-primary" />市场行情
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">A 股主要指数实时数据</p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: TrendingUp, label: "上涨", count: gainers, cls: "text-gain bg-gain/10 border-gain/20" },
            { icon: TrendingDown, label: "下跌", count: losers, cls: "text-loss bg-loss/10 border-loss/20" },
            { icon: Minus, label: "平盘", count: flat, cls: "text-muted-foreground bg-card border-border" },
          ].map(({ icon: Icon, label, count, cls }) => (
            <div key={label} className={`rounded-xl border p-4 flex items-center gap-3 ${cls}`}>
              <Icon className="w-5 h-5" />
              <div>
                <div className="font-mono text-2xl font-bold">{count}</div>
                <div className="text-[10px] uppercase tracking-widest opacity-70">{label}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-xl bg-card border border-border overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-7 gap-2 px-5 py-3 border-b border-border bg-surface-base">
            {["指数名称", "代码", "最新价", "涨跌额", "涨跌幅", "成交量", "高 / 低"].map(h => (
              <div key={h} className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">{h}</div>
            ))}
          </div>
          <div className="divide-y divide-border">
            {marketIndices.map(idx => {
              const up = idx.changePct > 0;
              const dn = idx.changePct < 0;
              return (
                <div key={idx.code} className="grid grid-cols-7 gap-2 px-5 py-4 hover:bg-surface-overlay transition-colors">
                  <div className="text-sm font-medium text-foreground self-center">{idx.name}</div>
                  <div className="font-mono text-xs text-muted-foreground self-center">{idx.code}</div>
                  <div className={cn("font-mono text-sm font-semibold self-center", up ? "text-gain" : dn ? "text-loss" : "text-foreground")}>
                    {idx.price.toFixed(2)}
                  </div>
                  <div className={cn("font-mono text-sm self-center", up ? "text-gain" : dn ? "text-loss" : "text-muted-foreground")}>
                    {up ? "+" : ""}{idx.change.toFixed(2)}
                  </div>
                  <div className="self-center">
                    <span className={cn("font-mono text-xs px-2 py-0.5 rounded font-semibold", up ? "text-gain bg-gain/15" : dn ? "text-loss bg-loss/15" : "text-muted-foreground bg-muted")}>
                      {up ? "+" : ""}{idx.changePct.toFixed(2)}%
                    </span>
                  </div>
                  <div className="font-mono text-sm text-muted-foreground self-center">{idx.volume}</div>
                  <div className="self-center space-y-0.5">
                    <div className="font-mono text-xs text-gain">{idx.high.toFixed(2)}</div>
                    <div className="font-mono text-xs text-loss">{idx.low.toFixed(2)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex items-start gap-3">
          <BarChart2 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="text-primary font-semibold">数据说明：</span>
            数据来源于新浪财经 API，交易时间工作日 9:30–15:00。主板 ±10%，科创/创业板 ±20%，北交所 ±30%。仅供参考，不构成投资建议。
          </p>
        </div>
      </div>
    </div>
  );
}
