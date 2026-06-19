import { useMarketIndices } from "@/hooks/useSupabaseData";
import { cn } from "@/lib/utils";

export default function MarketTickerBar() {
  const { data: indices } = useMarketIndices();
  if (!indices.length) return null;
  const items = [...indices, ...indices];

  return (
    <div className="shrink-0 overflow-hidden border-b border-border bg-card h-10 flex items-center">
      <div className="flex animate-marquee whitespace-nowrap">
        {items.map((idx, i) => (
          <span key={i} className="inline-flex items-center gap-2 px-6 border-r border-border h-10 shrink-0">
            <span className="text-xs font-medium text-muted-foreground">{idx.name}</span>
            <span className="font-mono text-xs font-semibold text-foreground">{Number(idx.price).toFixed(2)}</span>
            <span className={cn("font-mono text-xs px-1.5 py-0.5 rounded", Number(idx.change_pct) >= 0 ? "text-gain bg-gain/10" : "text-loss bg-loss/10")}>
              {Number(idx.change_pct) >= 0 ? "+" : ""}{Number(idx.change_pct).toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
