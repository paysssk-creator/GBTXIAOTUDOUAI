"""GBT v2.0 - Native Desktop Agent (OpenHuman Architecture)
Modular HTML: styles.css + layout.html + scripts.js -> combined at runtime
PyWebView native window (falls back to browser)
"""
import os,sys,threading,json,logging,time
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
logging.basicConfig(level=logging.INFO,format="%(message)s");L=logging.getLogger("GBT")

from flask import Flask,jsonify,request,render_template_string
from gbt.mcp import get_mcp,call_mcp
from gbt.providers import PROVIDERS,AutoKeyConfig

# ── Build homepage from modular files ──
TD=os.path.join(os.path.dirname(__file__),"templates")
C=open(os.path.join(TD,"styles.css"),encoding="utf-8").read()
H=open(os.path.join(TD,"layout.html"),encoding="utf-8").read()
J=open(os.path.join(TD,"scripts.js"),encoding="utf-8").read()
HP=f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>GBT v2.0 - AI Desktop Agent</title><style>{C}</style></head><body>{H}<script>{J}</script></body></html>'

# ── Agent Bridge ──
class B:
    def __init__(s):
        s.a=None
        try:
            from agents.gbt_agent import GBTAgent
            from tools.mcp_tools import register_all_mcp_tools
            s.a=GBTAgent(provider="auto",project_root=os.getcwd())
            register_all_mcp_tools(s.a._tools,os.getcwd())
            L.info(f"Agent: {s.a.llm.provider_name}")
        except Exception as e:
            L.warning(f"Agent init: {e} - demo mode")
    def chat(s,t):
        if s.a:return s.a.run(t)
        return "[Demo] GBT v2.0 running. Configure API keys for full AI."
    def reason(s,t,m="chain"):
        if s.a:
            r=s.a.deep_reason(t,m)
            return {"mode":r.mode.value,"conclusion":r.conclusion,"confidence":r.confidence}
        return {"mode":m,"conclusion":"[Demo] Full reasoning available with API keys.","confidence":1.0}
bridge=B()

# ── Flask API ──
app=Flask(__name__)
@app.route("/")
def home():return render_template_string(HP)

@app.route("/api/status")
def st():
    m=get_mcp();d=AutoKeyConfig.scan()
    return jsonify({"mcp_count":len(m.list_servers()),"llm":bridge.a.llm.provider_name if bridge.a else "Demo","model":bridge.a.llm.model if bridge.a else "N/A","keys_available":sum(1 for v in d.values() if v["status"]=="available"),"keys_total":len(PROVIDERS)})

@app.route("/api/providers")
def pr():
    d=AutoKeyConfig.scan();r={}
    for k,v in d.items():r[k]={"name":v["config"]["name"],"status":v["status"]}
    return jsonify(r)

@app.route("/api/mcp")
def mc():return jsonify({"servers":get_mcp().list_servers()})

@app.route("/api/mcp/<s>",methods=["POST"])
def mx(s):
    r=call_mcp(s)
    return jsonify({"ok":r.ok,"data":(r.data or "")[:2000],"error":r.error})

@app.route("/api/chat",methods=["POST"])
def ch():
    d=request.json or {}
    return jsonify({"response":bridge.chat(d.get("text",""))})

@app.route("/api/reason",methods=["POST"])
def rs():
    d=request.json or {}
    return jsonify(bridge.reason(d.get("text",""),d.get("mode","chain")))

# ── Launch ──
def launch():
    try:
        import webview as wv
        t=threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False),daemon=True)
        t.start();time.sleep(1.5)
        L.info("GBT Desktop window opening...")
        wv.create_window("GBT v2.0 - AI Desktop Agent","http://127.0.0.1:8765",width=1100,height=720,min_size=(900,600))
        wv.start()
    except ImportError:
        L.warning("pywebview not installed - browser mode");L.info("http://localhost:8765")
        app.run(host="127.0.0.1",port=8765,debug=False)

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--browser",action="store_true");a=p.parse_args()
    if a.browser:
        L.info("Browser: http://localhost:8765");app.run(host="127.0.0.1",port=8765,debug=False)
    else:launch()

if __name__=="__main__":main()
