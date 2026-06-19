import { marketIndices } from "@/data/mockData";
import { cn } from "@/lib/utils";

export default function MarketTickerBar() {
  const items = [...marketIndices, ...marketIndices];
  return (
    <div className="shrink-0 overflow-hidden border-b border-border bg-card h-10 flex items-center">
      <div className="flex animate-marquee whitespace-nowrap">
        {items.map((idx, i) => (
          <span key={i} className="inline-flex items-center gap-2 px-6 border-r border-border/40 h-10 shrink-0">
            <span className="text-xs font-medium text-muted-foreground">{idx.name}</span>
            <span className="font-mono text-xs font-semibold text-foreground">{idx.price.toFixed(2)}</span>
            <span className={cn("font-mono text-xs px-1.5 py-0.5 rounded", idx.changePct >= 0 ? "text-gain bg-gain/10" : "text-loss bg-loss/10")}>
              {idx.changePct >= 0 ? "+" : ""}{idx.changePct.toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
