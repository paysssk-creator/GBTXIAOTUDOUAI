"""GBT v2.0 Production Server — starts immediately with real LLM when available"""
import os, sys, json, platform
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, render_template_string, request
from gbt.mcp import get_mcp
from gbt.providers import PROVIDERS, AutoKeyConfig

app = Flask(__name__)

# Real LLM initialization
_llm = None
try:
    from gbt.llm import GBTLLM
    _llm = GBTLLM(provider="auto")
except Exception:
    pass

@app.route("/")
def home():
    tpl = os.path.join(os.path.dirname(__file__), "desktop", "templates", "homepage.html")
    if os.path.exists(tpl):
        with open(tpl, "r", encoding="utf-8") as f:
            return render_template_string(f.read())
    return "<h1>GBT v2.0</h1>"

@app.route("/api/status")
def status():
    mcp = get_mcp(); disc = AutoKeyConfig.scan()
    return jsonify({
        "mcp_servers": mcp.list_servers(),
        "mcp_count": len(mcp.list_servers()),
        "llm": _llm.provider_name if _llm else "Not configured", "model": _llm.model if _llm else "N/A",
        "keys_available": sum(1 for v in disc.values() if v["status"]=="available"),
        "keys_total": len(PROVIDERS),
        "platform": platform.system(), "python": platform.python_version(),
    })

@app.route("/api/providers")
def providers():
    disc = AutoKeyConfig.scan()
    r = {}
    for pid, info in disc.items():
        r[pid] = {"name": info["config"]["name"], "status": info["status"]}
    return jsonify(r)

@app.route("/api/mcp")
def mcp_list():
    return jsonify({"servers": get_mcp().list_servers()})

@app.route("/api/mcp/<s>", methods=["POST"])
def mcp_call(s):
    from gbt.mcp import call_mcp
    rr = call_mcp(s)
    return jsonify({"ok": rr.ok, "data": rr.data[:3000], "error": rr.error})

@app.route("/api/reason", methods=["POST"])
def reason():
    if not _llm:
        return jsonify({"ok": False, "error": "LLM not configured", "help": "Set API keys via .env for full reasoning"})
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

print("\n" + "=" * 60)
print("  GBT v2.0 Production Server - RUNNING!")
print(f"  http://localhost:8765  |  LLM: {_llm.provider_name if _llm else 'Not configured'}")
print("  API: /api/status | /api/providers | /api/mcp | /api/chat | /api/reason")
print("=" * 60 + "\n")

app.run(host="127.0.0.1", port=8765, debug=False)
