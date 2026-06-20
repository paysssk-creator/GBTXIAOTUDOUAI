"""GBT v2.1 — Fast Start Server (真实生产入口)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, render_template_string, request
from gbt.providers import PROVIDERS, AutoKeyConfig
from gbt.mcp import get_mcp
from gbt.llm import GBTLLM

app = Flask(__name__)
HP = os.path.join(os.path.dirname(__file__), "desktop", "templates", "homepage.html")
HPAGE = open(HP, "r", encoding="utf-8").read() if os.path.exists(HP) else ""

# 真实 LLM 初始化
_llm = None
try: _llm = GBTLLM(provider="auto")
except Exception: pass

@app.route("/")
def home():
    return render_template_string(HPAGE) if HPAGE else "<h1>GBT v2.1 — Production</h1>"

@app.route("/api/status")
def status():
    discovered = AutoKeyConfig.scan()
    available = sum(1 for v in discovered.values() if v["status"] == "available")
    mcp = get_mcp()
    return jsonify({
        "mcp_count": len(mcp.list_servers()),
        "llm": _llm.provider_name if _llm else "Not configured",
        "model": _llm.model if _llm else "N/A",
        "keys_available": available,
        "keys_total": len(PROVIDERS),
    })

@app.route("/api/providers")
def prov():
    discovered = AutoKeyConfig.scan()
    result = {}
    for pid, info in discovered.items():
        cfg = info["config"]
        result[pid] = {"name": cfg["name"], "status": info["status"],
                       "models": cfg.get("models", []), "pricing": cfg.get("pricing", "")}
    return jsonify(result)

@app.route("/api/mcp")
def mcp_list():
    mcp = get_mcp()
    return jsonify({"servers": mcp.list_servers()})

@app.route("/api/mcp/<s>", methods=["POST"])
def mcp_call(s):
    from gbt.mcp import call_mcp
    try:
        r = call_mcp(s)
        return jsonify({"ok": r.ok, "data": str(r.data)[:3000], "error": r.error})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/chat", methods=["POST"])
def chat():
    if not _llm:
        return jsonify({"ok": False, "error": "LLM not configured. Set API keys in .env file.",
                        "help": "See /api/providers for available providers"})
    try:
        d = request.json or {}
        msgs = [{"role": "user", "content": d.get("text", d.get("message", "Hello"))}]
        resp = _llm.invoke(msgs)
        return jsonify({"ok": True, "response": resp})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/reason", methods=["POST"])
def reason():
    if not _llm:
        return jsonify({"ok": False, "error": "LLM not configured", "help": "Set API keys to unlock reasoning"})
    try:
        from gbt.reasoner import DeepReasoner, ReasonMode as RM
        d = request.json or {}
        mode = RM(d.get("mode", "chain"))
        dr = DeepReasoner(_llm)
        result = dr.reason(d.get("text", d.get("question", "")), mode)
        return jsonify({"ok": True, "mode": result.mode.value, "conclusion": result.conclusion[:2000],
                        "confidence": result.confidence, "plan": result.plan[:10]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/market")
def market():
    try:
        from gbt.connectors.market import get_indices as _gi
        result = _gi()
        if result.get("ok"): return jsonify(result)
        return jsonify({"ok": False, "error": result.get("error", "Market data unavailable")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/agents/status")
def agents_status():
    try:
        from agents.gbt_agent import GBTAgent
        caps = 18
        return jsonify({"ok": True, "agents": {"agents": {"main": {"capabilities": caps, "description": "Primary agent"}},
                        "agents_running": 1, "total_capabilities": caps}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

print(f"GBT v2.1 Production — http://localhost:8765 — LLM: {_llm.provider_name if _llm else 'Not configured'}")
app.run(host="127.0.0.1", port=8765, debug=False)
