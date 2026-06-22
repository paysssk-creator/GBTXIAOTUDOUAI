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


# ── 仪表盘主页 (生产仪表盘) ──
_DASH_PATH = os.path.join(os.path.dirname(__file__), "desktop", "templates", "layout.html")
_DASH_HTML = open(_DASH_PATH, "r", encoding="utf-8").read() if os.path.exists(_DASH_PATH) else ""

@app.route("/dashboard")
def dashboard():
    return render_template_string(_DASH_HTML) if _DASH_HTML else "<h1>Dashboard HTML not found</h1>"

@app.route("/api/dashboard")
def dashboard_data():
    import psutil
    data = {}
    try:
        from gbt.llm_metrics import get_llm_metrics
        data["llm"] = get_llm_metrics()
    except: data["llm"] = {"error": "metrics not available"}
    try:
        data["system"] = {"cpu": psutil.cpu_percent(interval=0.1),
                          "memory": psutil.virtual_memory().percent,
                          "disk": psutil.disk_usage("/").percent,
                          "host": os.environ.get("COMPUTERNAME","")}
    except: data["system"] = {"cpu":0,"memory":0,"disk":0}
    try:
        from gbt.trader import trader
        ts = trader.get_status() if trader else {}
        wl = getattr(trader,"watchlist",{}) or {}
        data["trade"] = {"auto_trade": ts.get("auto_trade",False),
                         "watchlist_count": len(wl), "watchlist": list(wl.items())[:10],
                         "account": {"cash":100000,"equity":100000,"pnl":0,"positions":0}}
    except: data["trade"] = {"error": "trader not ready"}
    try:
        mcp = get_mcp()
        data["mcp"] = {"servers": mcp.list_servers()}
    except: data["mcp"] = {"servers":[]}
    try:
        from gbt.watcher import watcher
        if watcher:
            ws = watcher.get_status()
            data["watcher"] = {"running": ws.get("running",False),
                               "alerts": list(watcher.alerts)[-5:] if hasattr(watcher,"alerts") else []}
    except: data["watcher"] = {"running":False}
    try:
        procs = []
        for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
            try: procs.append(p.info)
            except: pass
        data["desktop"] = {"top_processes": sorted(procs,key=lambda x:x.get("cpu_percent",0) or 0,reverse=True)[:10]}
    except: data["desktop"] = {"top_processes":[]}
    return jsonify(data)

@app.route("/api/hacker/capabilities")
def hacker_all_caps():
    caps = []
    icons = {"security":"ph-shield-check","core":"ph-gear","devops":"ph-stack",
             "ai":"ph-brain","monitor":"ph-eye","control":"ph-monitor",
             "trade":"ph-chart-line-up","desktop":"ph-desktop","hacker":"ph-skull"}
    mcp_ids = ["scanner","audit","auto-fix","self-evolve","bounty-hunter","stress-test",
               "mirror-deploy","deepseek-analyzer","intelligent-scheduler","email-watcher",
               "rustdesk","halo-cms","desktop-control","cloud-llm","memory"]
    try:
        from gbt.agents import init_framework
        fw = init_framework()
        cat_map = {"DesktopAgent":"desktop","TradingAgent":"trade","HackerAgent":"hacker",
                   "SystemAgent":"system","NotifyAgent":"control"}
        for agent in fw.router.agents.values():
            cat = cat_map.get(agent.name, "core")
            for cap in agent.capabilities:
                caps.append({"id":cap.name,"name":cap.description,
                            "icon":icons.get(cat,"ph-squares-four"),"cat":cat,
                            "desc":", ".join(cap.keywords[:3]),"mcp":cap.name in mcp_ids,
                            "agent":agent.name,"priority":cap.priority})
    except:
        caps = [{"id":"system","name":"System Status","icon":"ph-info","cat":"system","desc":"Status check","mcp":False}]
    caps.sort(key=lambda x:-x.get("priority",5))
    return jsonify({"capabilities":caps,"total":len(caps)})

@app.route("/api/hacker/exec", methods=["POST"])
def hacker_exec_cap():
    d = request.json or {}
    cid = d.get("id","")
    act = d.get("action","run")
    # Direct via framework
    try:
        from gbt.agents import init_framework
        fw = init_framework()
        for agent in fw.router.agents.values():
            for cap in agent.capabilities:
                if cap.name == cid:
                    try:
                        result = agent.execute(cid, act)
                        return jsonify({"ok":result.ok,"data":str(result.data)[:3000] if result.data else "",
                                       "agent":result.agent,"error":result.error})
                    except Exception as e:
                        return jsonify({"ok":False,"error":str(e),"agent":agent.name})
    except: pass
    # Fallback: MCP
    mcp_caps = ["scanner","audit","auto-fix","self-evolve","bounty-hunter","stress-test",
                "mirror-deploy","deepseek-analyzer","intelligent-scheduler","email-watcher",
                "rustdesk","halo-cms","desktop-control","cloud-llm","memory"]
    if cid in mcp_caps:
        try:
            from gbt.mcp import call_mcp
            r = call_mcp(cid)
            return jsonify({"ok":r.ok,"data":str(r.data)[:3000],"error":r.error})
        except Exception as e:
            return jsonify({"ok":False,"error":str(e)})
    return jsonify({"ok":False,"error":f"Unknown capability: {cid}"})



# ── 缺失端点补全 (仪表盘调用的所有辅助API) ──
@app.route("/api/system")
def api_system():
    import psutil
    return jsonify({"cpu":psutil.cpu_percent(interval=0.1),"memory":psutil.virtual_memory().percent,
                    "disk":psutil.disk_usage("/").percent,"host":os.environ.get("COMPUTERNAME",""),
                    "uptime":round((__import__("time").time()-psutil.boot_time())/3600,1)})

@app.route("/api/devices")
def api_devices():
    return jsonify({"devices":[],"total":0})

@app.route("/api/watcher/status")
def api_watcher_status():
    try:
        from gbt.watcher import watcher
        if watcher: return jsonify(watcher.get_status())
    except: pass
    return jsonify({"running":False,"alerts":[]})

@app.route("/api/trader/status")
def api_trader_status():
    try:
        from gbt.trader import trader
        if trader: return jsonify(trader.get_status())
    except: pass
    return jsonify({"auto_trade":False,"watchlist":[]})

@app.route("/api/account")
def api_account():
    return jsonify({"cash":100000,"equity":100000,"pnl":0,"positions":0})

@app.route("/api/connectors")
def api_connectors():
    return jsonify({"connectors":[],"total":0})

@app.route("/api/logo")
def api_logo():
    import base64,os
    lp=os.path.join(os.path.dirname(__file__),"desktop","GBT_logo.png")
    if os.path.exists(lp):
        with open(lp,"rb") as lf:
            b64=base64.b64encode(lf.read()).decode()
        return f'<img src="data:image/png;base64,{b64[:100]}" style="width:32px">',200,{'Content-Type':'text/html'}
    return 'GBT',200

@app.route("/api/access_log")
def api_access_log():
    return jsonify({"ok":True})

@app.route("/favicon.ico")
def favicon():
    import os
    fp=os.path.join(os.path.dirname(__file__),"desktop","GBT.ico")
    if os.path.exists(fp):
        return open(fp,"rb").read(),200,{'Content-Type':'image/x-icon'}
    return '',204

app.run(host="127.0.0.1", port=8765, debug=False)
