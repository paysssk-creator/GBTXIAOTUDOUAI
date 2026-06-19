
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const body = await req.json();
    const { type, data } = body;

    if (!type || !data) {
      return new Response(
        JSON.stringify({ error: "Missing 'type' or 'data' field" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    let result;

    switch (type) {
      case "system_status": {
        // Upsert single row
        const { error } = await supabase
          .from("system_status")
          .upsert({ ...data, updated_at: new Date().toISOString() }, { onConflict: "id" });
        if (error) throw error;
        result = { success: true, type: "system_status" };
        break;
      }

      case "agents": {
        // Upsert array of agents
        const agents = Array.isArray(data) ? data : [data];
        const rows = agents.map((a: Record<string, unknown>) => ({
          id: a.id,
          name: a.name,
          role: a.role,
          status: a.status || "offline",
          tasks: a.tasks || 0,
          last_active: a.last_active || a.lastActive || "0s",
          memory: a.memory || "0 MB",
          model: a.model || "N/A",
          updated_at: new Date().toISOString(),
        }));
        const { error } = await supabase.from("agents").upsert(rows, { onConflict: "id" });
        if (error) throw error;
        result = { success: true, type: "agents", count: rows.length };
        break;
      }

      case "market_indices": {
        const indices = Array.isArray(data) ? data : [data];
        const rows = indices.map((m: Record<string, unknown>) => ({
          code: m.code,
          name: m.name,
          price: m.price,
          change: m.change,
          change_pct: m.change_pct ?? m.changePct ?? 0,
          volume: m.volume || "0",
          high: m.high || 0,
          low: m.low || 0,
          updated_at: new Date().toISOString(),
        }));
        const { error } = await supabase.from("market_indices").upsert(rows, { onConflict: "code" });
        if (error) throw error;
        result = { success: true, type: "market_indices", count: rows.length };
        break;
      }

      case "audit_report": {
        const { error } = await supabase.from("audit_reports").insert({
          passed_count: data.summary?.passed ?? data.passed_count ?? 0,
          warnings_count: data.summary?.warnings ?? data.warnings_count ?? 0,
          failed_count: data.summary?.failed ?? data.failed_count ?? 0,
          passed_items: data.passed_items ?? data.passed ?? [],
          warning_items: data.warning_items ?? data.warnings ?? [],
          failed_items: data.failed_items ?? data.failed ?? [],
          v12_details: data.v12_details ?? data.v12 ?? {},
        });
        if (error) throw error;
        result = { success: true, type: "audit_report" };
        break;
      }

      default:
        return new Response(
          JSON.stringify({ error: `Unknown type: ${type}` }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
    }

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("data-ingest error:", error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
