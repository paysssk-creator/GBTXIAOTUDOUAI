import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";

// Generic hook for fetching table data with realtime
function useTable<T>(table: string, orderCol?: string) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      let q = supabase.from(table).select("*");
      if (orderCol) q = q.order(orderCol);
      const { data: rows } = await q;
      if (rows) setData(rows as T[]);
      setLoading(false);
    };
    fetch();

    const channel = supabase
      .channel(`${table}_changes`)
      .on("postgres_changes", { event: "*", schema: "public", table }, (payload) => {
        if (payload.eventType === "INSERT") {
          setData(prev => [...prev, payload.new as T]);
        } else if (payload.eventType === "UPDATE") {
          setData(prev => prev.map(row => {
            const r = row as Record<string, unknown>;
            const n = payload.new as Record<string, unknown>;
            return r.id === n.id || r.code === n.code ? payload.new as T : row;
          }));
        } else if (payload.eventType === "DELETE") {
          setData(prev => prev.filter(row => {
            const r = row as Record<string, unknown>;
            const o = payload.old as Record<string, unknown>;
            return r.id !== o.id && r.code !== o.code;
          }));
        }
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [table, orderCol]);

  return { data, loading };
}

export interface SystemStatusRow {
  id: string; llm: string; provider: string; model: string;
  mcp_count: number; keys_available: number; keys_total: number;
  uptime: string; version: string; updated_at: string;
}

export interface AgentRow {
  id: string; name: string; role: string; status: string;
  tasks: number; last_active: string; memory: string; model: string;
  updated_at: string;
}

export interface MarketIndexRow {
  code: string; name: string; price: number; change: number;
  change_pct: number; volume: string; high: number; low: number;
  updated_at: string;
}

export interface V12Details {
  compile?: { passed: number; total: number };
  api?: { passed: number; total: number };
  router?: { passed: number; total: number };
  runtime?: string;
  threadSafety?: string;
  logic?: string;
  typeSafety?: string;
}

export interface AuditReportRow {
  id: string; timestamp: string;
  passed_count: number; warnings_count: number; failed_count: number;
  passed_items: string[]; warning_items: Array<{ name: string; detail: string }>;
  failed_items: string[]; v12_details: V12Details;
}

export function useSystemStatus() {
  const { data, loading } = useTable<SystemStatusRow>("system_status");
  return { status: data[0] ?? null, loading };
}

export function useAgents() {
  return useTable<AgentRow>("agents", "id");
}

export function useMarketIndices() {
  return useTable<MarketIndexRow>("market_indices", "code");
}

export function useAuditReport() {
  const [report, setReport] = useState<AuditReportRow | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      const { data } = await supabase
        .from("audit_reports")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (data) setReport(data as AuditReportRow);
      setLoading(false);
    };
    fetch();
  }, []);

  return { report, loading };
}
