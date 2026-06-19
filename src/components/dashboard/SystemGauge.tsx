import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface Props { label: string; value: number; detail?: string; }

function gaugeColor(v: number) {
  if (v >= 90) return { stroke: "hsl(var(--loss))", cls: "text-loss" };
  if (v >= 70) return { stroke: "hsl(var(--warning))", cls: "text-warning" };
  return { stroke: "hsl(var(--gain))", cls: "text-gain" };
}

export default function SystemGauge({ label, value, detail }: Props) {
  const [animated, setAnimated] = useState(0);
  const R = 36;
  const circ = 2 * Math.PI * R;
  const { stroke, cls } = gaugeColor(value);

  useEffect(() => { const t = setTimeout(() => setAnimated(value), 150); return () => clearTimeout(t); }, [value]);

  return (
    <div className="flex flex-col items-center gap-2 p-4 rounded-xl bg-card border border-border">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r={R} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
          <circle cx="44" cy="44" r={R} fill="none" stroke={stroke} strokeWidth="6"
            strokeLinecap="round" strokeDasharray={circ}
            strokeDashoffset={circ - (animated / 100) * circ}
            style={{ transition: "stroke-dashoffset 600ms cubic-bezier(.4,0,.2,1)", filter: `drop-shadow(0 0 5px ${stroke})` }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn("font-mono text-lg font-semibold leading-none", cls)}>{value}%</span>
        </div>
      </div>
      <div className="text-center">
        <div className="text-[10px] font-semibold tracking-widest uppercase text-muted-foreground">{label}</div>
        {detail && <div className="font-mono text-[10px] text-muted-foreground mt-0.5">{detail}</div>}
      </div>
    </div>
  );
}
