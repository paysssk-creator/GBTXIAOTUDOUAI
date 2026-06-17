"""GBT v2.0 - Desktop Agent (OpenHuman Architecture)
LLM switching + failover + real 6-step evolve
"""
import os,sys,threading,json,logging,time,subprocess

# ── 路径初始化 ──
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,_here)                          # exe同级目录
sys.path.insert(0,os.path.join(_here,".."))       # 开发模式
sys.path.insert(0,os.path.join(os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else _here,".."))

# ── 加载 .env (多路径fallback, 手动解析避免 python-dotenv 报错) ──
def _load_env_force():
    """多路径强制加载 .env，去重避免重复"""
    raw_paths=[]
    if getattr(sys,'frozen',False):
        raw_paths=[
            os.path.join(os.path.dirname(sys.executable),".env"),
            os.path.join(sys._MEIPASS,".env"),
        ]
    else:
        raw_paths=[os.path.join(_here,".env"),os.path.join(_here,"..",".env")]
    paths=[]
    seen=set()
    for _p in raw_paths:
        _rp=os.path.normpath(os.path.abspath(_p))
        if _rp not in seen and os.path.exists(_rp):
            seen.add(_rp); paths.append(_rp)
    for _p in paths:
        try:
            with open(_p,"r",encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        k,v=line.split("=",1)
                        k=k.strip();v=v.strip().strip('"').strip("'")
                        if k and v:
                            os.environ[k]=v
                            if 'KEY' in k.upper():
                                mask=v[:8]+"..."+v[-4:] if len(v)>12 else "***"
                                print(f"ENV: {k}={mask}")
        except Exception as _e:
            print(f"ENV FAIL: {_p} -> {_e}")
_load_env_force()

logging.basicConfig(level=logging.INFO,format="%(message)s");L=logging.getLogger("GBT")
from flask import Flask,jsonify,request,render_template_string
from gbt.mcp import get_mcp,call_mcp
from gbt.providers import PROVIDERS,AutoKeyConfig
from gbt.connectors.registry import get_registry as get_connectors

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
J=open(os.path.join(TD,"scripts.js"),encoding="utf-8").read() if os.path.exists(os.path.join(TD,"scripts.js")) else ""
HP=f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>GBT Pro</title><link rel="icon" href="/favicon.ico" type="image/x-icon"><style>{C}</style></head><body>{H}</body></html>'

# ── LLM Manager with failover ──
class LLMMgr:
    def __init__(s,prov="auto"):s.a=None;s.prov=None;s.model=None;s.try_init(prov=prov)
    def try_init(s,prov="auto"):
        from gbt.llm import GBTLLM
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
@app.route("/favicon.ico")
def favicon():
    import flask
    ico = os.path.join(os.path.dirname(__file__),"GBT.ico")
    if os.path.exists(ico):
        return flask.send_file(ico,mimetype="image/x-icon")
    return "",204

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
@app.route("/api/market")
def mk():
    import urllib.request
    indices = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指', 'sh000688': '科创50', 'sh000300': '沪深300', 'sz399005': '中小100'}
    codes = ",".join(indices.keys())
    try:
        req = urllib.request.Request("http://hq.sinajs.cn/list=" + codes, headers={"Referer": "https://finance.sina.com.cn"})
        raw = urllib.request.urlopen(req, timeout=5).read().decode("gbk")
        result = []
        import re
        for line in raw.strip().split("\n"):
            m = re.search(r"(sh\d+|sz\d+)", line)
            if not m: continue
            code = m.group(0)
            pm = re.search(r'="(.+)"', line)
            if not pm: continue
            parts = pm.group(1).split(",")
            if len(parts) < 4: continue
            name = indices.get(code, parts[0])
            price = float(parts[3]) if parts[3] else 0
            prev = float(parts[2]) if parts[2] else 0
            chg = round(price - prev, 2)
            chgp = round(chg / prev * 100, 2) if prev else 0
            result.append({"code": code, "name": name, "price": price, "change": chg, "changePct": chgp})
        return jsonify({"indices": result, "updated": True})
    except Exception as e:
        return jsonify({"indices": [], "error": str(e), "updated": False})


@app.route("/api/system")
def sy():
    import ctypes, ctypes.wintypes, time
    try:
        # CPU via GetSystemTimes
        class FILETIME(ctypes.Structure):
            _fields_=[("dwLowDateTime",ctypes.wintypes.DWORD),("dwHighDateTime",ctypes.wintypes.DWORD)]
        idle0, kernel0, user0 = FILETIME(), FILETIME(), FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle0), ctypes.byref(kernel0), ctypes.byref(user0))
        time.sleep(0.3)
        idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1))
        def ft_to_u64(ft): return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
        idle_d = ft_to_u64(idle1) - ft_to_u64(idle0)
        kernel_d = ft_to_u64(kernel1) - ft_to_u64(kernel0)
        user_d = ft_to_u64(user1) - ft_to_u64(user0)
        total = kernel_d + user_d
        cpu = round((total - idle_d) / total * 100, 1) if total > 0 else 0
        # Memory via GlobalMemoryStatusEx
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_=[("dwLength",ctypes.wintypes.DWORD),("dwMemoryLoad",ctypes.wintypes.DWORD),
                ("ullTotalPhys",ctypes.c_uint64),("ullAvailPhys",ctypes.c_uint64),
                ("ullTotalPageFile",ctypes.c_uint64),("ullAvailPageFile",ctypes.c_uint64),
                ("ullTotalVirtual",ctypes.c_uint64),("ullAvailVirtual",ctypes.c_uint64),
                ("ullAvailExtendedVirtual",ctypes.c_uint64)]
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        mem_pct = mem.dwMemoryLoad
        used_gb = round((mem.ullTotalPhys - mem.ullAvailPhys) / (1024**3), 1)
        total_gb = round(mem.ullTotalPhys / (1024**3), 1)
        return jsonify({"cpu":cpu,"memory":mem_pct,"memory_used_gb":used_gb,"memory_total_gb":total_gb})
    except Exception as e:
        return jsonify({"cpu":0,"memory":0,"memory_used_gb":0,"memory_total_gb":0,"error":str(e)})
@app.route("/api/devices")
def dv():
    """Real device inventory via WMI"""
    import subprocess
    def _ps(cmd):
        try:
            r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,timeout=8)
            return r.stdout.strip()
        except:return ""
    gpus=[]
    try:
        ps_cmd='Get-CimInstance Win32_VideoController | Select Name,AdapterRAM,DriverVersion | ConvertTo-Json'
        out=_ps(ps_cmd)
        if out:
            import json as _j
            items=_j.loads(out) if out.startswith('[') else [_j.loads(out)]
            for i in items:
                ram=i.get('AdapterRAM',0) or 0
                gpus.append({'name':i.get('Name','GPU'),'ram_mb':round(ram/(1024*1024),0) if ram else 0,'driver':i.get('DriverVersion','')})
    except:gpus=[{'name':'GPU Info Unavailable','ram_mb':0,'driver':''}]
    audio=[]
    try:
        out=_ps('Get-CimInstance Win32_SoundDevice | Select Name,Status | ConvertTo-Json')
        if out:
            import json as _j
            items=_j.loads(out) if out.startswith('[') else [_j.loads(out)]
            for i in items:audio.append({'name':i.get('Name','Audio'),'status':i.get('Status','OK')})
    except:pass
    disks=[]
    try:
        out=_ps('Get-CimInstance Win32_DiskDrive | Select Model,Size | ConvertTo-Json')
        if out:
            import json as _j
            items=_j.loads(out) if out.startswith('[') else [_j.loads(out)]
            for i in items:
                sz=i.get('Size',0) or 0
                disks.append({'model':(i.get('Model','Disk') or '').strip(),'size_gb':round(sz/(1024**3),0)})
    except:pass
    net=[]
    try:
        out=_ps('Get-CimInstance Win32_NetworkAdapter | Where-Object {$_.NetEnabled -eq $true} | Select Name,Speed | ConvertTo-Json')
        if out:
            import json as _j
            items=_j.loads(out) if out.startswith('[') else [_j.loads(out)]
            for i in items:
                sp=i.get('Speed',0) or 0
                net.append({'name':i.get('Name','Network'),'speed_mbps':round(sp/(1000*1000),0) if sp else 0})
    except:pass
    # Disk usage
    du_total=0;du_used=0;du_free=0
    try:
        import ctypes
        free=ctypes.c_uint64();total=ctypes.c_uint64();tfree=ctypes.c_uint64()
        ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\",ctypes.byref(free),ctypes.byref(total),ctypes.byref(tfree))
        du_total=round(total.value/(1024**3),1)
        du_free=round(free.value/(1024**3),1)
        du_used=round(du_total-du_free,1)
    except:pass
    return jsonify({"gpu":gpus,"audio":audio,"disks":disks,"network":net,"disk_c":{"total_gb":du_total,"used_gb":du_used,"free_gb":du_free}})

@app.route("/api/connectors")
def cn():
    """List all connectors/plugins with status."""
    reg = get_connectors()
    return jsonify({"connectors": reg.list_all(), "by_category": reg.list_by_category()})

@app.route("/api/connectors/<cid>/connect",methods=["POST"])
def cn_connect(cid):
    reg = get_connectors()
    return jsonify(reg.connect(cid))

@app.route("/api/connectors/<cid>/disconnect",methods=["POST"])
def cn_disconnect(cid):
    reg = get_connectors()
    reg.disconnect(cid)
    return jsonify({"ok":True,"status":"disconnected"})

@app.route("/api/connectors/<cid>/action",methods=["POST"])
def cn_action(cid):
    """Execute a native connector action."""
    d = request.json or {}
    act = d.get("action","")
    args = d.get("args",{})
    r = {"ok":False,"error":"Unknown action"}
    # ── Filesystem ──
    if cid == "filesystem":
        p = args.get("path","")
        if act == "list" and p:
            try:
                items = []
                for f in os.listdir(p):
                    fp = os.path.join(p,f)
                    items.append({"name":f,"is_dir":os.path.isdir(fp),"size":os.path.getsize(fp) if os.path.isfile(fp) else 0})
                r = {"ok":True,"path":p,"items":items[:50]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "read" and p:
            try:
                with open(p,"r",encoding="utf-8",errors="replace") as f:
                    r = {"ok":True,"content":f.read()[:5000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "write" and p:
            try:
                with open(p,"w",encoding="utf-8") as f: f.write(args.get("content",""))
                r = {"ok":True,"written":len(args.get("content",""))}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Terminal ──
    elif cid == "terminal":
        cmd = args.get("cmd","")
        if act == "exec" and cmd:
            try:
                res = subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30,cwd=args.get("cwd") or os.path.expanduser("~"))
                r = {"ok":True,"stdout":res.stdout[:3000],"stderr":res.stderr[:1000],"code":res.returncode}
            except subprocess.TimeoutExpired: r = {"ok":False,"error":"Timeout (30s)"}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Git ──
    elif cid == "git":
        repo = args.get("repo",os.path.dirname(os.path.dirname(__file__)))
        if act == "status":
            try:
                res = subprocess.run("git status --short",shell=True,capture_output=True,text=True,timeout=10,cwd=repo)
                r = {"ok":True,"output":res.stdout,"branch":subprocess.run("git branch --show-current",shell=True,capture_output=True,text=True,cwd=repo).stdout.strip()}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "log":
            try:
                res = subprocess.run("git log --oneline -10",shell=True,capture_output=True,text=True,timeout=10,cwd=repo)
                r = {"ok":True,"commits":res.stdout.strip().split("\n") if res.stdout else []}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Process Manager ──
    elif cid == "process":
        if act == "list":
            try:
                res = subprocess.run("tasklist /fo csv /nh",shell=True,capture_output=True,text=True,timeout=10)
                procs = []
                for line in res.stdout.strip().split("\n")[:30]:
                    parts = line.replace('"','').split(",")
                    if len(parts)>=2: procs.append({"name":parts[0].strip(),"pid":parts[1].strip()})
                r = {"ok":True,"processes":procs}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Display / Screenshot ──
    elif cid == "display":
        if act == "screenshot":
            try:
                import tempfile
                tmp = os.path.join(tempfile.gettempdir(),"gbt_screenshot.png")
                # Uses pyautogui if available
                try:
                    import pyautogui
                    img = pyautogui.screenshot()
                    img.save(tmp)
                    r = {"ok":True,"path":tmp,"size":os.path.getsize(tmp)}
                except ImportError:
                    # Fallback to PowerShell
                    ps = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds | ConvertTo-Json"
                    res = subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,timeout=10)
                    r = {"ok":True,"display_info":res.stdout.strip()[:500]}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Market ──
    elif cid == "market":
        if act == "get_indices":
            try:
                import urllib.request,re
                indices = {'sh000001':'SSE','sz399001':'SZSE','sz399006':'ChiNext','sh000688':'STAR50','sh000300':'CSI300','sz399005':'SME100'}
                codes = ",".join(indices.keys())
                req = urllib.request.Request("http://hq.sinajs.cn/list="+codes,headers={"Referer":"https://finance.sina.com.cn"})
                raw = urllib.request.urlopen(req,timeout=5).read().decode("gbk")
                result = []
                for line in raw.strip().split("\n"):
                    m = re.search(r"(sh\d+|sz\d+)",line)
                    if not m: continue
                    pm = re.search(r'="(.+)"',line)
                    if not pm: continue
                    parts = pm.group(1).split(",")
                    if len(parts)<4: continue
                    result.append({"code":m.group(0),"name":indices.get(m.group(0),parts[0]),"price":float(parts[3] or 0),"change":round(float(parts[3] or 0)-float(parts[2] or 0),2)})
                r = {"ok":True,"indices":result}
            except Exception as e: r = {"ok":False,"error":str(e)}
    return jsonify(r)

@app.route("/api/reason",methods=["POST"])
def rs():
    d=request.json or {};
    if not llm.a:return jsonify({"mode":"demo","conclusion":"No LLM available.","confidence":0})
    from gbt.reasoner import DeepReasoner,ReasonMode as RM
    dr=DeepReasoner(llm.a);mode=getattr(RM,d.get("mode","CHAIN").upper(),RM.CHAIN)
    r=dr.reason(d.get("text",""),mode)
    return jsonify({"mode":r.mode.value,"conclusion":r.conclusion,"confidence":r.confidence,"steps":len(r.nodes)})

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
