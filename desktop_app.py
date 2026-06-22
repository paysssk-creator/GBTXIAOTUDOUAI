"""GBT Pro v2.1 - Native Desktop App (pywebview)"""
import sys,os,threading,time
sys.path.insert(0,os.path.dirname(__file__))
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"desktop"))
try:import webview
except:webview=None
from flask import Flask,render_template_string,jsonify,request

DP=os.path.join(os.path.dirname(__file__),"desktop","templates","layout.html")
DASH_HTML=open(DP,"r",encoding="utf-8").read() if os.path.exists(DP) else "<h1>GBT Pro</h1>"
from gbt.knowledge.inject import inject_knowledge
inject_knowledge()
app=Flask(__name__)

@app.route("/")
@app.route("/dashboard")
def dashboard():
    dp=os.path.join(os.path.dirname(__file__),"desktop","templates","layout.html")
    html=open(dp,"r",encoding="utf-8").read() if os.path.exists(dp) else "<h1>Dashboard not found</h1>"
    resp=app.make_response(render_template_string(html))
    resp.headers['Cache-Control']='no-cache,no-store,must-revalidate'
    resp.headers['Pragma']='no-cache'
    resp.headers['Expires']='0'
    return resp

@app.route("/api/status")
def status():
    from gbt.providers import AutoKeyConfig
    from gbt.mcp import get_mcp
    discovered=AutoKeyConfig.scan()
    avail=sum(1 for v in discovered.values() if v["status"]=="available")
    return jsonify({"mcp_count":len(get_mcp().list_servers()),"llm":"Akashic/DeepSeek/Ollama","model":"auto","keys_available":avail,"keys_total":13})

@app.route("/api/dashboard")
def dashboard_data():
    import psutil;data={}
    try: from gbt.llm_metrics import get_llm_metrics;data["llm"]=get_llm_metrics()
    except: data["llm"]={}
    try: data["system"]={"cpu":psutil.cpu_percent(interval=0.1),"memory":psutil.virtual_memory().percent,"disk":psutil.disk_usage("/").percent,"host":os.environ.get("COMPUTERNAME","")}
    except: data["system"]={}
    try: from gbt.mcp import get_mcp;data["mcp"]={"servers":get_mcp().list_servers()}
    except: data["mcp"]={"servers":[]}
    try:
        import gbt.paper_account as __pa
        pa=__pa.get_status()
        data["trade"]={"account":pa,"watchlist":data.get("trade",{}).get("watchlist",[])}
    except: data["trade"]={"account":{"cash":100000,"equity":100000,"pnl":0},"watchlist":[]}
    return jsonify(data)

@app.route("/api/hacker/capabilities")
def hacker_all_caps():
    caps=[];icons={"desktop":"ph-desktop","hacker":"ph-skull","trade":"ph-chart-line-up","system":"ph-gear","control":"ph-monitor"}
    mcp_ids=["scanner","audit","auto-fix","self-evolve","bounty-hunter","stress-test","mirror-deploy","deepseek-analyzer","intelligent-scheduler","email-watcher","rustdesk","halo-cms","desktop-control","cloud-llm","memory"]
    try:
        from gbt.agents import init_framework;fw=init_framework()
        cat_map={"DesktopAgent":"desktop","TradingAgent":"trade","HackerAgent":"hacker","SystemAgent":"system","NotifyAgent":"control"}
        for agent in fw.router.agents.values():
            cat=cat_map.get(agent.name,"core")
            for cap in agent.capabilities: caps.append({"id":cap.name,"name":cap.description,"icon":icons.get(cat,"ph-squares-four"),"cat":cat,"desc":", ".join(cap.keywords[:3]),"mcp":cap.name in mcp_ids,"agent":agent.name,"priority":cap.priority})
    except: caps=[{"id":"system","name":"System","icon":"ph-info","cat":"system"}]
    caps.sort(key=lambda x:-x.get("priority",5));return jsonify({"capabilities":caps,"total":len(caps)})

@app.route("/api/hacker/exec",methods=["POST"])
def hacker_exec_cap():
    d=request.json or{};cid=d.get("id","");act=d.get("action","run")
    try:
        from gbt.agents import init_framework;fw=init_framework()
        for agent in fw.router.agents.values():
            for cap in agent.capabilities:
                if cap.name==cid:
                    try: result=agent.execute(cid,act);return jsonify({"ok":result.ok,"data":str(result.data)[:3000] if result.data else "","agent":result.agent,"error":result.error})
                    except Exception as e:return jsonify({"ok":False,"error":str(e)})
    except: pass
    mcp_ids=["scanner","audit","auto-fix","self-evolve","bounty-hunter","stress-test","mirror-deploy","deepseek-analyzer","intelligent-scheduler","email-watcher","rustdesk","halo-cms","desktop-control","cloud-llm","memory"]
    if cid in mcp_ids:
        try:
            from gbt.mcp import call_mcp
            r=call_mcp(cid,timeout=3)
            return jsonify({"ok":r.ok,"data":str(r.data)[:3000] if r.data else "","error":r.error})
        except Exception as e:return jsonify({"ok":False,"error":f"MCP timeout: {str(e)[:50]}"})
    return jsonify({"ok":False,"error":f"Unknown:{cid}"})

@app.route("/api/providers")
def prov():
    from gbt.providers import AutoKeyConfig;discovered=AutoKeyConfig.scan();result={}
    for pid,info in discovered.items():result[pid]={"name":info["config"]["name"],"status":info["status"]}
    return jsonify(result)

@app.route("/api/system")
def api_system():
    import psutil;return jsonify({"cpu":psutil.cpu_percent(0.1),"memory":psutil.virtual_memory().percent,"disk":psutil.disk_usage("/").percent,"host":os.environ.get("COMPUTERNAME",""),"uptime":round((time.time()-psutil.boot_time())/3600,1)})

@app.route("/api/devices")
def api_devices():return jsonify({"devices":[],"total":0})
@app.route("/api/watcher/status")
def api_watcher_status():return jsonify({"running":False})
@app.route("/api/trader/status")
def api_trader_status():return jsonify({"auto_trade":False})
@app.route("/api/account")
def api_account():import gbt.paper_account as __pa;return jsonify(__pa.get_status())
@app.route("/api/connectors")
def api_connectors():return jsonify({"connectors":[],"total":0})
@app.route("/api/logo")
def api_logo():return '<svg width="32" height="32"><rect width="32" height="32" rx="6" fill="#6366f1"/><text x="16" y="22" text-anchor="middle" fill="white" font-size="16" font-weight="bold">G</text></svg>',200,{'Content-Type':'image/svg+xml'}
@app.route("/api/access_log")
def api_access_log():return jsonify({"ok":True})
@app.route("/styles.css")
def styles():
    import os
    sp=os.path.join(os.path.dirname(__file__),"desktop","templates","styles.css")
    if os.path.exists(sp):return open(sp,"r",encoding="utf-8").read(),200,{"Content-Type":"text/css"}
    return "",404

@app.route("/favicon.ico")
def favicon():return "",204

@app.route("/api/market")
def market():
    try:
        from gbt.connectors.market import get_indices as _gi
        return jsonify(_gi())
    except: return jsonify({"ok":False,"error":"Market not available"})

if __name__=="__main__":
    print("GBT Pro v2.1 - Desktop App")
    threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False),daemon=True).start()
    time.sleep(3)
    webview.create_window("GBT Pro v2.1","http://127.0.0.1:8765/dashboard",width=1280,height=800,min_size=(1000,650))
    webview.start()
