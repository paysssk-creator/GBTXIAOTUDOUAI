"""GBT v2.0 Demo Server - starts immediately, no LLM needed"""
import os, sys, json, platform
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, render_template_string
from gbt.mcp import get_mcp
from gbt.providers import PROVIDERS, AutoKeyConfig

app = Flask(__name__)

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
        "llm": "Demo", "model": "N/A",
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
    return jsonify({"mode":"demo","conclusion":"Demo mode - set API keys for full reasoning","confidence":1.0})

@app.route("/api/chat", methods=["POST"])
def chat():
    from flask import request
    return jsonify({"response":"[Demo Mode] GBT v2.0 is running! Set API keys in .env for full AI capabilities."})

print("\n" + "=" * 60)
print("  GBT v2.0 Demo Server - RUNNING!")
print("  http://localhost:8765")
print("  API: /api/status | /api/providers | /api/mcp | /api/chat | /api/reason")
print("=" * 60 + "\n")

app.run(host="127.0.0.1", port=8765, debug=False)
