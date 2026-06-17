"""GBT v2.0 - Fast Start Server"""
from flask import Flask, jsonify, render_template_string, request
import os, platform

app = Flask(__name__)
HP = os.path.join(os.path.dirname(__file__), "desktop", "templates", "homepage.html")
HPAGE = open(HP, "r", encoding="utf-8").read() if os.path.exists(HP) else ""

@app.route("/")
def home():
    return render_template_string(HPAGE) if HPAGE else "<h1>GBT v2.0</h1>"

@app.route("/api/status")
def status():
    return jsonify({"mcp_count":19,"llm":"Demo","model":"N/A","keys_available":4,"keys_total":13,"platform":platform.system(),"python":platform.python_version()})

@app.route("/api/providers")
def prov():
    return jsonify({"zhipu":{"name":"GLM","status":"available"},"openai":{"name":"OpenAI","status":"missing"},"deepseek":{"name":"DeepSeek","status":"available"},"ollama":{"name":"Ollama","status":"check_port"},"kimi":{"name":"Kimi","status":"available"}})

@app.route("/api/mcp")
def mcp(): return jsonify({"servers":["scanner","audit","self-evolve","auto-fix","mirror-deploy","stress-test","bounty-hunter","deepseek-analyzer"]})

@app.route("/api/mcp/<s>", methods=["POST"])
def mc(s): return jsonify({"ok":True,"data":"[Demo] MCP/"+s+" - configure real server"})

@app.route("/api/chat", methods=["POST"])
def chat():
    return jsonify({"response":"[Demo] GBT v2.0 running! Set API keys in .env to unlock full AI with 13 LLMs."})

@app.route("/api/reason", methods=["POST"])
def reason():
    d = request.json or {}
    return jsonify({"mode":d.get("mode","chain"),"conclusion":"[Demo] 8 reasoning modes available. Set API keys to unlock.","confidence":1.0})

print("GBT v2.0 http://localhost:8765")
app.run(host="127.0.0.1", port=8765, debug=False)
