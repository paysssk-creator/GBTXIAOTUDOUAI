"""GBT v2.0 - Desktop Agent (OpenHuman Architecture)
LLM switching + failover + real 6-step evolve
"""
import os,sys,threading,json,logging,time,subprocess

# ── 路径初始化 ──
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,_here)                          # exe同级目录
sys.path.insert(0,os.path.join(_here,".."))       # 开发模式
sys.path.insert(0,os.path.join(os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else _here,".."))

# ── 加载 .env (多路径fallback) ──
from dotenv import dotenv_values as _dotenv_values
def _load_env_force():
    """多路径强制加载 .env，输出debug信息"""
    paths=[]
    if getattr(sys,'frozen',False):
        paths=[
            os.path.join(os.path.dirname(sys.executable), ".env"),
            os.path.join(sys._MEIPASS, ".env"),
            os.path.join(sys._MEIPASS, "..", ".env"),
        ]
    else:
        paths=[os.path.join(_here, ".env"), os.path.join(_here, "..", ".env")]
    for _p in paths:
        if os.path.exists(_p):
            try:
                vals=_dotenv_values(_p)
                for k,v in vals.items():
                    if v:
                        os.environ[k]=v
                        if 'KEY' in k.upper():
                            mask=v[:8]+"..."+v[-4:] if len(v)>12 else "***"
                            print(f"ENV LOAD: {k}={mask} from {_p}")
            except Exception as _e:
                print(f"ENV FAIL: {_p} -> {_e}")
_load_env_force()

logging.basicConfig(level=logging.INFO,format="%(message)s");L=logging.getLogger("GBT")
from flask import Flask,jsonify,request,render_template_string
from gbt.mcp import get_mcp,call_mcp
from gbt.providers import PROVIDERS,AutoKeyConfig

# ── Build homepage ──
# ── 模板路径 (兼容打包模式) ──
if getattr(sys,'frozen',False):
    _base = sys._MEIPASS
    TD = os.path.join(_base,"desktop","templates")
    if not os.path.isdir(TD):
        TD = os.path.join(_base,"templates")
else:
    TD = os.path.join(os.path.dirname(__file__),"templates")
C=open(os.path.join(TD,"styles.css"),encoding="utf-8").read()
H=open(os.path.join(TD,"layout.html"),encoding="utf-8").read()
J=open(os.path.join(TD,"scripts.js"),encoding="utf-8").read()
HP=f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>GBT</title><style>{C}</style></head><body>{H}<script>{J}</script></body></html>'

# ── LLM Manager with failover ──
class LLMMgr:
    def __init__(s,prov="auto"):s.a=None;s.prov=None;s.model=None;s.try_init(prov=prov)
    def try_init(s,prov="auto"):
        from gbt.llm import GBTLLM
        # 再次确保 .env 已加载
        _load_env_force()
        disc=AutoKeyConfig.scan()
        valid=[p for p,i in disc.items() if i["status"]=="available"]
        if prov!="auto" and prov in valid:valid.insert(0,prov)
        if not valid:
            s.a=None;s.prov=None;L.warning("No keys - demo mode");return False
        p=valid[0]
        try:s.a=GBTLLM(provider=p,timeout=120);s.prov=p;s.model=s.a.model;L.info(f"LLM: {PROVIDERS[p]['name']} | {s.model}");return True
        except Exception as e:
            L.warning(f"LLM {p}: {e} - demo mode")
            s.a=None;s.prov=None;return False
    def switch(s,prov):
        r=s.try_init(prov);return {"ok":r,"provider":s.prov,"model":s.model,"name":PROVIDERS[s.prov]["name"] if s.prov else "Demo"}
    def chat(s,t):
        if not s.a:return "[Demo] No LLM available."
        try:
            msgs=[{"role":"system","content":"You are GBT, a helpful AI desktop agent."},{"role":"user","content":t}]
            return s.a.invoke(msgs)
        except Exception as e:return f"[Error] {e}"

llm=LLMMgr(prov="deepseek")

# ── Flask API ──
app=Flask(__name__)
@app.route("/")
def home(): return render_template_string(HP)

@app.route("/api/status")
def st():
    m=get_mcp();d=AutoKeyConfig.scan()
    return jsonify({"mcp_count":len(m.list_servers()),"llm":PROVIDERS[llm.prov]["name"] if llm.prov else "Demo","model":llm.model or "N/A","keys_available":sum(1 for v in d.values() if v["status"]=="available"),"keys_total":len(PROVIDERS)})

@app.route("/api/providers")
def pr():
    d=AutoKeyConfig.scan();r={}
    for k,v in d.items():r[k]={"name":v["config"]["name"],"status":v["status"],"models":v["config"]["models"]}
    return jsonify(r)

@app.route("/api/switch",methods=["POST"])
def sw():
    d=request.json or {};p=d.get("provider","auto");res=llm.switch(p)
    return jsonify(res)

@app.route("/api/models")
def ml():
    d=AutoKeyConfig.scan();r={}
    for k,v in d.items():
        if v["status"]=="available":r[k]={"name":v["config"]["name"],"models":v["config"]["models"],"default":v["config"]["default_model"]}
    return jsonify(r)

@app.route("/api/mcp")
def mc():return jsonify({"servers":get_mcp().list_servers()})

@app.route("/api/mcp/<s>",methods=["POST"])
def mx(s):
    r=call_mcp(s);return jsonify({"ok":r.ok,"data":(r.data or "")[:2000],"error":r.error})

@app.route("/api/chat",methods=["POST"])
def ch():
    d=request.json or {};t=d.get("text","")
    if not t:return jsonify({"response":"Please enter a message."})
    return jsonify({"response":llm.chat(t),"provider":llm.prov,"model":llm.model})

@app.route("/api/reason",methods=["POST"])
def rs():
    d=request.json or {};
    if not llm.a:return jsonify({"mode":"demo","conclusion":"No LLM available.","confidence":0})
    from gbt.reasoner import DeepReasoner,ReasonMode as RM
    dr=DeepReasoner(llm.a);mode=getattr(RM,d.get("mode","CHAIN").upper(),RM.CHAIN)
    r=dr.reason(d.get("text",""),mode)
    return jsonify({"mode":r.mode.value,"conclusion":r.conclusion,"confidence":r.confidence,"steps":len(r.steps)})

@app.route("/api/evolve",methods=["POST"])
def ev():
    """Real 6-step evolution loop"""
    project=os.path.dirname(os.path.dirname(__file__))
    steps=[]
    try:
        from gbt.evolve import EvolveEngine
        eng=EvolveEngine(project,dry_run=False,strong=False)
        rpt=eng.run(desc="Desktop-triggered evolve")
        return jsonify({"ok":rpt.success,"summary":rpt.summary or "Completed","steps":len(rpt.steps),"rollback":rpt.rollback})
    except Exception as e:return jsonify({"ok":False,"error":str(e)[:500]})


def launch():
    try:
        import webview as wv
        t=threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8766,debug=False,use_reloader=False),daemon=True)
        t.start();time.sleep(1.5)
        L.info("Desktop window opening...");wv.create_window("GBT","http://127.0.0.1:8766",width=1100,height=720,min_size=(900,600));wv.start()
    except ImportError:
        L.warning("Browser mode");L.info("http://localhost:8765");app.run(host="127.0.0.1",port=8765,debug=False)

def main():
    import argparse;p=argparse.ArgumentParser();p.add_argument("--browser",action="store_true");a=p.parse_args()
    if a.browser:L.info("http://localhost:8766");app.run(host="127.0.0.1",port=8766,debug=False)
    else:launch()

if __name__=="__main__":main()
