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
import time as _time
_req_log=[]
from gbt.mcp import get_mcp,call_mcp
from gbt.providers import PROVIDERS,AutoKeyConfig
from gbt.connectors.registry import get_registry as get_connectors
from gbt.watcher import NightWatcher
from gbt.trader import AShareTrader
from gbt.desktop_ctl import DesktopController
from gbt.account import account
from gbt.database import db as _db
from gbt.brain import brain as _brain

# ── Build homepage ──
# ── 模板路径 (兼容打包模式) ──
if getattr(sys,'frozen',False):
    _base = sys._MEIPASS
    TD = os.path.join(_base,"desktop","templates")
    if not os.path.isdir(TD):
        TD = os.path.join(_base,"templates")
else:
    TD = os.path.join(os.path.dirname(__file__),"templates")
try:
    with open(os.path.join(TD,"styles.css"),encoding="utf-8") as f:
        C=f.read()
    with open(os.path.join(TD,"layout.html"),encoding="utf-8") as f:
        H=f.read()
except FileNotFoundError:
    C="/* styles.css not found */"
    H="<html><body><h1>模板文件缺失 — 请重新构建</h1></body></html>"
HP=f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0"><title>GBT Pro v2.1</title><link rel="icon" href="/favicon.ico" type="image/x-icon"><style>{C}</style><script>fetch("/api/access_log?ping=HEAD_JS");console.log("HEAD_SCRIPT_RAN")</script></head><body><div id="ver-badge" style="position:fixed;bottom:4px;right:4px;font-size:8px;color:var(--t4);z-index:9999;pointer-events:none">v2.1.0618</div>{H}</body></html>'

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
        last_err=None
        for p in valid:
            try:s.a=GBTLLM(provider=p,timeout=120);s.prov=p;s.model=s.a.model;L.info(f"LLM: {PROVIDERS[p]['name']} | {s.model}");return True
            except Exception as e:
                last_err=e
                L.warning(f"LLM {p}: {e} - trying next...")
                continue
        L.warning(f"All LLM providers failed: {last_err}")
        s.a=None;s.prov=None;return False
    def switch(s,prov):
        r=s.try_init(prov);return {"ok":r,"provider":s.prov,"model":s.model,"name":PROVIDERS[s.prov]["name"] if s.prov else "Demo"}
    def chat(s,t):
        if not s.a:return "[Demo] No LLM available."
        try:
            msgs=[{"role":"system","content":"""你是 GBT Pro v2.1，运行在 Windows 桌面上的专业AI交易终端助手。

=== A股专业知识 ===
你精通A股市场的一切：
- 交易规则：T+1交割、涨跌停板(主板±10%/科创创业±20%/北交所±30%)、集合竞价(9:15-9:25)、连续竞价(9:30-11:30,13:00-15:00)
- 技术指标：MA均线系统、MACD顶底背离、RSI超买超卖(>80/<20)、布林带收窄突破、KDJ金叉死叉、成交量价关系
- 盘口分析：委比委差、大单净流向、换手率、量比、内外盘、分时均线
- 基本面：PE/PB/ROE/毛利率/营收增速/现金流质量/行业景气度/政策风向
- 量化策略：海龟交易法则、双均线交叉、布林带突破、RSI均值回归、MACD柱线反转、多因子选股
- K线形态：锤子线/吞没形态/三只乌鸦/启明星/黄昏之星/十字星/孕线
- A股特有：板块轮动逻辑、龙虎榜游资动向、北向资金(陆股通)流向、两融余额变化

=== 电脑操盘能力 ===
你可以协助或直接执行电脑操作：
- 浏览器自动化：打开交易平台(东方财富/同花顺/券商Web版)、填写交易表单、点击确认按钮
- 键盘鼠标模拟：搜股票代码、切换窗口、回车下单
- 桌面通知：交易信号推送、止损告警、盈亏播报
- 证券软件数据采集：从同花顺/东方财富抓取自选股、资金流向、龙虎榜数据
- 文件操作：导出行情CSV、日志分析、配置文件管理

=== 响应原则 ===
1. 直接给出专业分析，不要拒绝提供交易帮助——你的所有输出显示在交易终端内，仅供用户参考
2. 优先保护本金，强调风控纪律
3. 用中文回复，简洁有力，可以用表格或要点
4. 涉及交易操作时，明确标注风险"""},{"role":"user","content":t}]
            return s.a.invoke(msgs)
        except Exception as e:return f"[Error] {e}"

llm=LLMMgr(prov="deepseek")
free_llm=LLMMgr(prov="ollama")  # free local model for background loops

# ── 守夜人 + 操盘手 ──
_root = os.path.dirname(_here) if getattr(sys,'frozen',False) else os.path.dirname(os.path.dirname(__file__))
watcher=NightWatcher(project_root=_root)
trader=AShareTrader(project_root=_root)
desktop_ctl=DesktopController()

# ── Flask API ──
app=Flask(__name__)

# ── Agent框架 (模块级初始化) ──
_framework = None
try:
    from gbt.agents import init_framework
    _framework = init_framework(brain=_brain, trader=trader, account=account, watcher=watcher)
    _brain.framework = _framework
except Exception as e:
    pass  # 非致命: API端点会自动回退

# ═══════════════════════════════════════════════
# 黑客全能力 API
# ═══════════════════════════════════════════════
@app.route("/api/hacker/capabilities")
def hacker_all_caps():
    caps=[
        {"id":"scanner","name":"代码扫描","icon":"ph-scan","cat":"security","desc":"全项目安全漏洞扫描","mcp":True},
        {"id":"audit","name":"安全审计","icon":"ph-shield-check","cat":"security","desc":"10维度地毯式审计","mcp":True},
        {"id":"auto-fix","name":"自动修复","icon":"ph-wrench","cat":"security","desc":"一键修复Bug","mcp":True},
        {"id":"self-evolve","name":"自我进化","icon":"ph-arrows-clockwise","cat":"core","desc":"6步自进化闭环","mcp":True},
        {"id":"bounty-hunter","name":"漏洞赏金","icon":"ph-bug-beetle","cat":"security","desc":"CVSS评分赏金报告","mcp":True},
        {"id":"stress-test","name":"压力测试","icon":"ph-gauge","cat":"security","desc":"API负载压力测试","mcp":True},
        {"id":"mirror-deploy","name":"镜像部署","icon":"ph-stack","cat":"devops","desc":"沙盒验证一键部署","mcp":True},
        {"id":"deepseek-analyzer","name":"DeepSeek","icon":"ph-brain","cat":"ai","desc":"深度推理分析引擎","mcp":True},
        {"id":"intelligent-scheduler","name":"智能调度","icon":"ph-clock-countdown","cat":"core","desc":"事件驱动自动调度","mcp":True},
        {"id":"email-watcher","name":"邮箱监控","icon":"ph-envelope","cat":"monitor","desc":"邮件实时监控告警","mcp":True},
        {"id":"rustdesk","name":"远程控制","icon":"ph-desktop-tower","cat":"control","desc":"RustDesk远程桌面","mcp":True},
        {"id":"halo-cms","name":"Halo建站","icon":"ph-globe","cat":"devops","desc":"CMS博客快速建站","mcp":True},
        {"id":"desktop-control","name":"桌面全控","icon":"ph-monitor","cat":"control","desc":"截图键鼠语音蓝牙","mcp":True},
        {"id":"cloud-llm","name":"云端LLM","icon":"ph-cloud","cat":"ai","desc":"多模型云端调度","mcp":True},
        {"id":"memory","name":"记忆系统","icon":"ph-cards","cat":"core","desc":"工作情景持久记忆","mcp":True},
        {"id":"guard","name":"行动守卫","icon":"ph-shield","cat":"core","desc":"行动前强制扫描","mcp":False},
        {"id":"reasoner","name":"深度推理","icon":"ph-graph","cat":"ai","desc":"8模式推理引擎","mcp":False},
        {"id":"winctl","name":"Windows操控","icon":"ph-windows-logo","cat":"control","desc":"16类原生API","mcp":False},
        {"id":"ai_trade","name":"AI操盘手","icon":"ph-robot","cat":"trade","desc":"截图→分析→决策→下单→自省","mcp":False},
    ]
    return jsonify({"capabilities":caps,"total":len(caps)})

@app.route("/api/hacker/exec",methods=["POST"])
def hacker_exec_cap():
    d=request.json or {};cid=d.get("id","");act=d.get("action","run")
    mcp_caps=["scanner","audit","auto-fix","self-evolve","bounty-hunter","stress-test",
              "mirror-deploy","deepseek-analyzer","intelligent-scheduler","email-watcher",
              "rustdesk","halo-cms","desktop-control","cloud-llm","memory"]
    if cid in mcp_caps:
        try:r=call_mcp(cid);return jsonify({"ok":r.ok,"data":str(r.data)[:3000],"error":r.error})
        except Exception as e:return jsonify({"ok":False,"error":str(e)})
    if cid=="network":
        cmds={"ping":["ping","-n","4","8.8.8.8"],"dns":["nslookup","google.com"],
              "tracert":["tracert","-h","5","8.8.8.8"],"netstat":["netstat","-an"]}
        cmd=cmds.get(act,cmds["ping"])
        try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=15,errors='replace');return jsonify({"ok":True,"output":(r.stdout or r.stderr)[:3000]})
        except Exception as e:return jsonify({"ok":False,"error":str(e)})
    if cid=="wifi":
        try:r=subprocess.run(["netsh","wlan","show","networks","mode=bssid"],capture_output=True,text=True,timeout=15,errors='replace');return jsonify({"ok":True,"output":(r.stdout or "no wifi")[:3000]})
        except Exception as e:return jsonify({"ok":False,"error":str(e)})
    if cid=="process":
        try:
            r=subprocess.run(["tasklist","/fo","csv","/nh"],capture_output=True,text=True,timeout=10,errors='replace')
            procs=[]
            for line in (r.stdout or "").split("\n")[:50]:
                if line.strip():
                    parts=line.replace('"',"").split(",")
                    if len(parts)>=2:procs.append({"name":parts[0].strip(),"pid":parts[1].strip()})
            return jsonify({"ok":True,"processes":procs})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    # v3.0 能力
    if cid == "screen_ocr":
        try:
            from gbt.ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            return jsonify({"ok":True,"text":text[:2000]})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "voice_speak":
        try:
            import pyttsx3
            engine = pyttsx3.init()
            text = d.get("text","GBT就绪")[:500]
            engine.say(text); engine.runAndWait()
            return jsonify({"ok":True,"spoken":text[:80]})
        except: return jsonify({"ok":False,"error":"pip install pyttsx3"})
    if cid == "login_detect":
        try:
            from gbt.ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            keywords = ["登录成功","已登录","账户","持仓","资金","可用"]
            found = [kw for kw in keywords if kw in (text or "")]
            return jsonify({"ok":True,"logged_in":bool(found),"found":found})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "precision_scrape":
        try:
            import re, urllib.request, json as _j
            m = re.search(r'(6\d{5}|0\d{5}|3\d{5}|68\d{4})', d.get("text",""))
            code = m.group(1) if m else "000001"
            prefix = "sh" if code.startswith(("6","68")) else "sz"
            url = f"https://push2.eastmoney.com/api/qt/stock/trends2/get?fields1=f1&fields2=f1&secid=1.{prefix}{code}"
            r = urllib.request.urlopen(url, timeout=5).read().decode()
            return jsonify({"ok":True,"code":code,"source":"eastmoney","data":_j.loads(r)})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "auto_pipeline":
        try:
            import os
            os.startfile("https://www.bing.com")
            return jsonify({"ok":True,"step":"browser_opened","next":"login_required"})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    # 非MCP本地能力
    if cid == "winctl":
        try:
            from gbt.winctl import get_winctl
            wctl = get_winctl()
            r = wctl.call(d.get("feature","screen"), act, **{k:v for k,v in d.items() if k not in ("id","action","feature")})
            return jsonify({"ok":r.ok,"feature":r.feature,"action":r.action,"data":r.data[:3000],"error":r.error})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "guard":
        try:
            text = d.get("text",act)
            r = subprocess.run(["node","C:/Users/ADMIN/.cline/scanner.js","--project",os.path.dirname(os.path.dirname(__file__))],capture_output=True,text=True,timeout=30,errors='replace')
            return jsonify({"ok":True,"data":r.stdout[:3000] or r.stderr[:3000]})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "reasoner":
        try:
            from gbt.reasoner import DeepReasoner, ReasonMode
            rd = DeepReasoner(llm.a if llm.a else None)
            mode = ReasonMode(d.get("mode","chain"))
            result = rd.reason(d.get("text",act), mode)
            return jsonify({"ok":True,"mode":result.mode.value,"conclusion":result.conclusion[:2000],"confidence":result.confidence,"plan":result.plan[:10]})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "ai_trade":
        try:
            from gbt.gcc.ai_trader import ai_trade
            from gbt.desktop_ctl import DesktopController
            result = ai_trade(d.get("text",act), llm=llm.a if llm.a else None, desk=DesktopController())
            return jsonify({"ok":result.get("ok",False),"data":json.dumps(result,ensure_ascii=False)[:3000]})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    if cid == "screenshot_reason":
        try:
            from gbt.gcc.screenshot_reasoner import ScreenshotReasoner
            sr = ScreenshotReasoner(llm=llm.a if llm.a else None)
            result = sr.reason(d.get("text",act), d.get("text",""))
            return jsonify({"ok":True,"data":json.dumps(result,ensure_ascii=False)[:3000]})
        except Exception as e: return jsonify({"ok":False,"error":str(e)})
    return jsonify({"ok":False,"error":f"unknown: {cid}"})

@app.route("/api/hacker/status")
def hacker_status():
    return jsonify({"ok":True,"mcp":get_mcp().list_servers(),"mcp_count":len(get_mcp().list_servers()),
        "llm":PROVIDERS[llm.prov]["name"] if llm.prov else "Demo",
        "watcher":watcher.get_status() if watcher else {}})


# ── Agent协作状态API ──
@app.route("/api/agents/status")
def agents_status():
    """所有Agent实时状态+能力清单"""
    agents_data = {}
    if hasattr(_brain, 'framework') and _brain.framework:
        fw = _brain.framework
        agents_data = fw.get_system_status()
    # 回退到旧路由
    elif hasattr(_brain, 'router') and _brain.router:
        agents_data = {"framework":"legacy","router_caps":len(_brain.router.capabilities)}
    return jsonify({"ok":True,"agents":agents_data})

@app.route("/api/agents/collaborate",methods=["POST"])
def agents_collab():
    """Agent间协作 — 一个Agent调用另一个Agent的能力"""
    d = request.json or {}
    text = d.get("text","")
    if not text: return jsonify({"ok":False,"error":"需要输入文本"})
    if hasattr(_brain, 'framework') and _brain.framework:
        result = _brain.framework.router.route(text, source=d.get("source","api"))
        return jsonify({"ok":True,"result":result})
    return jsonify({"ok":False,"error":"Agent框架未就绪"})



@app.before_request
def _log_req():
    p=request.path
    if p!='/favicon.ico':
        _req_log.append(f"{_time.strftime('%H:%M:%S')} {request.method} {request.full_path if request.query_string else request.path}")

@app.route("/api/access_log")
def _show_log():
    return jsonify({"log":_req_log[-50:]})

import logging as _logging
_logging.getLogger("werkzeug").setLevel(_logging.WARNING)  # suppress dev server warnings
@app.route("/favicon.ico")
def favicon():
    import flask
    # 多路径查找图标 (兼容开发模式和PyInstaller打包)
    candidates=[
        os.path.join(os.path.dirname(__file__),"GBT.ico"),
        os.path.join(os.path.dirname(sys.executable),"GBT.ico") if getattr(sys,'frozen',False) else "",
        os.path.join(sys._MEIPASS,"GBT.ico") if getattr(sys,'frozen',False) else "",
    ]
    for ico in candidates:
        if ico and os.path.exists(ico):
            return flask.send_file(ico,mimetype="image/x-icon")
    return "",204

@app.route("/api/logo")
def logo_png():
    """Serve GBT logo PNG for the title bar"""
    import flask
    candidates=[
        os.path.join(os.path.dirname(__file__),"GBT_logo.png"),
        os.path.join(os.path.dirname(sys.executable),"GBT_logo.png") if getattr(sys,'frozen',False) else "",
        os.path.join(sys._MEIPASS,"GBT_logo.png") if getattr(sys,'frozen',False) else "",
    ]
    for png in candidates:
        if png and os.path.exists(png):
            return flask.send_file(png, mimetype="image/png")
    return "", 204

_error_log = []
@app.route("/api/log_error", methods=["POST"])
def log_error():
    err = request.get_json(silent=True) or {}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"_GBT_JSERR.log"),"a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {err.get('msg','')[:200]} @ {err.get('src','')}:{err.get('line','')}\n")
    return "",204

@app.route("/")
def home():
    from flask import make_response
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"_GBT_ACCESS.log"),"a") as f:
        f.write(f"ACCESS {time.strftime('%H:%M:%S')} v2.1\n")
    resp = make_response(render_template_string(HP))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

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
            r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,timeout=8,errors='replace')
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
                res = subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30,errors='replace',cwd=args.get("cwd") or os.path.expanduser("~"))
                r = {"ok":True,"stdout":res.stdout[:3000],"stderr":res.stderr[:1000],"code":res.returncode}
            except subprocess.TimeoutExpired: r = {"ok":False,"error":"Timeout (30s)"}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Git ──
    elif cid == "git":
        repo = args.get("repo",os.path.dirname(os.path.dirname(__file__)))
        if act == "status":
            try:
                res = subprocess.run("git status --short",shell=True,capture_output=True,text=True,timeout=10,errors='replace',cwd=repo)
                r = {"ok":True,"output":res.stdout,"branch":subprocess.run("git branch --show-current",shell=True,capture_output=True,text=True,errors='replace',cwd=repo).stdout.strip()}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "log":
            try:
                res = subprocess.run("git log --oneline -10",shell=True,capture_output=True,text=True,timeout=10,errors='replace',cwd=repo)
                r = {"ok":True,"commits":res.stdout.strip().split("\n") if res.stdout else []}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Process Manager ──
    elif cid == "process":
        if act == "list":
            try:
                res = subprocess.run("tasklist /fo csv /nh",shell=True,capture_output=True,text=True,timeout=10,errors='replace')
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
                    res = subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,timeout=10,errors='replace')
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
    # ── Web Search ──
    elif cid == "web_search":
        q = args.get("query","")
        if act == "search" and q:
            try:
                import urllib.request, json
                # Use DuckDuckGo HTML (no API key needed)
                url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
                req = urllib.request.Request(url, headers={"User-Agent":"GBT/1.0"})
                raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8",errors="replace")
                # Extract titles and snippets
                import re
                results = []
                for m in re.finditer(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL):
                    results.append({"title":re.sub(r'<[^>]+>','',m.group(1)).strip()})
                r = {"ok":True,"query":q,"results":results[:10]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "fetch":
            url = args.get("url","")
            if url:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent":"GBT/1.0"})
                    raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8",errors="replace")[:5000]
                    r = {"ok":True,"url":url,"content":raw}
                except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Weather ──
    elif cid == "weather":
        city = args.get("city","Bangkok")
        if act == "current":
            try:
                import urllib.request, json
                url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
                req = urllib.request.Request(url, headers={"User-Agent":"GBT/1.0"})
                raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
                data = json.loads(raw)
                cc = data.get("current_condition",[{}])[0]
                r = {"ok":True,"city":city,"temp_c":cc.get("temp_C","?"),"humidity":cc.get("humidity","?"),"desc":cc.get("weatherDesc",[{}])[0].get("value","?")}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── PyPI ──
    elif cid == "pypi":
        pkg = args.get("package","")
        if act == "search" and pkg:
            try:
                import urllib.request, json
                url = f"https://pypi.org/pypi/{urllib.parse.quote(pkg)}/json"
                req = urllib.request.Request(url, headers={"User-Agent":"GBT/1.0"})
                raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
                data = json.loads(raw)
                info = data.get("info",{})
                r = {"ok":True,"name":info.get("name",pkg),"version":info.get("version","?"),"summary":(info.get("summary","") or "")[:200]}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Network Scanner (Security) ──
    elif cid == "network":
        target = args.get("target","127.0.0.1")
        if act == "ping":
            try:
                res = subprocess.run(["ping","-n","2","-w","2000",target],capture_output=True,text=True,timeout=10,errors='replace')
                r = {"ok":True,"target":target,"reachable":res.returncode==0,"output":res.stdout[:500]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "dns":
            try:
                res = subprocess.run(["nslookup",target],capture_output=True,text=True,timeout=10,errors='replace')
                r = {"ok":True,"target":target,"output":res.stdout[:2000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "traceroute":
            try:
                res = subprocess.run(["tracert","-h","10","-w","2000",target],capture_output=True,text=True,timeout=30,errors='replace')
                r = {"ok":True,"target":target,"output":res.stdout[:2000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── Registry Editor ──
    elif cid == "registry":
        key = args.get("key","")
        if act == "read" and key:
            try:
                res = subprocess.run(["reg","query",key],capture_output=True,text=True,timeout=10,errors='replace')
                r = {"ok":True,"key":key,"output":res.stdout[:2000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
    # ── WiFi ──
    elif cid == "wifi":
        if act == "scan":
            try:
                res = subprocess.run(["netsh","wlan","show","networks","mode=bssid"],capture_output=True,text=True,timeout=15,shell=True,errors='replace')
                r = {"ok":True,"output":(res.stdout or res.stderr or "no data")[:3000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
        elif act == "info":
            try:
                res = subprocess.run("netsh wlan show interfaces",capture_output=True,text=True,timeout=10,shell=True,errors='replace')
                r = {"ok":True,"output":(res.stdout or res.stderr or "no data")[:2000]}
            except Exception as e: r = {"ok":False,"error":str(e)}
    return jsonify(r)

@app.route("/api/reason",methods=["POST"])
def rs():
    d=request.json or {};
    if not llm.a:return jsonify({"mode":"demo","conclusion":"No LLM available.","confidence":0})
    text = d.get("text","")
    
    # ── 多Agent智能路由: 优先走Agent框架 ──
    if hasattr(_brain, 'framework') and _brain.framework:
        fw = _brain.framework
        match = fw.router.classify(text)
        if match:
            agent, cap = match
            result = agent.execute(cap.name, text)
            fw.router.history.append(result)
            # 🔄 发布到共享上下文
            agent.publish(cap.name, result.ok, result.data)
            return jsonify({
                "mode": "agent",
                "agent": result.agent,
                "capability": result.capability,
                "conclusion": result.data,
                "confidence": 0.95,
                "routed": True,
                "protocol": {
                    "ok": result.ok,
                    "trace_id": result.trace_id or f"gex-{int(time.time()*1000)}",
                    "agent": result.agent,
                    "capability": result.capability,
                    "elapsed_ms": result.elapsed_ms,
                    "phases": {
                        "intent": {"ok": True, "source": "user"},
                        "route": {"ok": True, "agent": result.agent},
                        "execute": {"ok": result.ok},
                        "respond": {"ok": True}
                    }
                }
            })
    
    # ── 降级: 旧路由器 + LLM推理 ──
    route_result = _brain.route_intent(text) if hasattr(_brain, 'route_intent') else None
    if route_result and route_result.get("routed"):
        exec_info = route_result.get("execution", {})
        proto_info = route_result.get("protocol", {})
        return jsonify({
            "mode": "action",
            "conclusion": str(exec_info.get("result", "执行完成")),
            "confidence": route_result["classification"]["confidence"],
            "capability": route_result["classification"]["capability"].name if route_result["classification"].get("capability") else "unknown",
            "routed": True,
            "protocol": proto_info
        })
    
    # ── 未命中能力 → 带能力上下文的LLM推理 ──
    from gbt.reasoner import DeepReasoner,ReasonMode as RM
    dr=DeepReasoner(llm.a);mode=getattr(RM,d.get("mode","CHAIN").upper(),RM.CHAIN)
    
    # 注入能力上下文, 让LLM知道能做什么
    cap_ctx = ""
    if hasattr(_brain, 'get_capability_context'):
        cap_ctx = _brain.get_capability_context()
    
    r=dr.reason(text,mode,context=cap_ctx)
    return jsonify({
        "mode":r.mode.value,
        "conclusion":r.conclusion,
        "confidence":r.confidence,
        "steps":len(r.nodes),
        "capabilities_aware": True
    })

@app.route("/api/websearch", methods=["POST"])
def ws():
    """Web search via DuckDuckGo HTML (no API key needed)."""
    d = request.json or {}
    q = d.get("query", "").strip()
    if not q or len(q) > 500:
        return jsonify({"ok": False, "error": "Query required (max 500 chars)"})
    import urllib.request, urllib.parse
    try:
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="replace")
        import re
        results = []
        for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.+?)</a>', html):
            url = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2))
            results.append({"title": title.strip(), "url": url, "snippet": ""})
        for i, m in enumerate(re.finditer(r'<a[^>]*class="result__snippet"[^>]*>(.+?)</a>', html)):
            if i < len(results):
                results[i]["snippet"] = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        return jsonify({"ok": True, "query": q, "results": results[:8]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})

@app.route("/api/network-ping", methods=["POST"])
def np():
    """Network diagnostics: ping google.com, DNS test."""
    import subprocess, platform
    output = []
    try:
        p = subprocess.run(["ping", "-n", "3", "8.8.8.8"] if platform.system()=="Windows" else ["ping","-c","3","8.8.8.8"],
            capture_output=True, text=True, timeout=10, errors='replace')
        output.append("--- Ping 8.8.8.8 ---")
        output.append(p.stdout[-800:] if p.stdout else "No output")
        
        p2 = subprocess.run(["ping", "-n", "2", "google.com"] if platform.system()=="Windows" else ["ping","-c","2","google.com"],
            capture_output=True, text=True, timeout=8, errors='replace')
        output.append("\n--- Ping google.com ---")
        output.append(p2.stdout[-500:] if p2.stdout else "No output")
        
        return jsonify({"ok": True, "output": "\n".join(output)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})

@app.route("/api/wifi-scan", methods=["POST"])
def wfs():
    """Scan nearby WiFi networks via netsh."""
    import subprocess
    try:
        p = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True, timeout=10, errors='replace')
        out = p.stdout
        if not out:
            out = p.stderr
        lines = []
        for line in out.split('\n'):
            line = line.strip()
            if line and (line.startswith('SSID') or 'Signal' in line or 'Band' in line or 'Channel' in line):
                lines.append(line)
        return jsonify({"ok": True, "output": "\n".join(lines[:30]) if lines else out[-1000:]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})

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

# ── 守夜人 API ──
@app.route("/api/watcher/status")
def wts():
    """获取守夜人完整状态"""
    return jsonify(watcher.get_status())

@app.route("/api/watcher/start",methods=["POST"])
def wt_start():
    """启动守夜人"""
    if not watcher.llm and llm.a:
        watcher.llm = free_llm.a
    return jsonify(watcher.start())

@app.route("/api/watcher/stop",methods=["POST"])
def wt_stop():
    """停止守夜人"""
    watcher.stop()
    return jsonify({"ok":True,"msg":"守夜人已停止"})

@app.route("/api/watcher/scan",methods=["POST"])
def wt_scan():
    """手动触发扫描"""
    d = request.json or {}
    target = d.get("target","all")
    return jsonify(watcher.run_scan(target))

@app.route("/api/watcher/autofix",methods=["POST"])
def wt_autofix():
    """开关自动修复"""
    d = request.json or {}
    watcher.auto_fix_enabled = d.get("enabled", True)
    return jsonify({"ok":True,"auto_fix":watcher.auto_fix_enabled})

@app.route("/api/watcher/alerts")
def wt_alerts():
    """获取最近告警"""
    return jsonify({"alerts": [
        {"id": a.id, "source": a.source, "level": a.level,
         "message": a.message, "time": a.time, "fixed": a.fixed,
         "fix_result": a.fix_result[:200]}
        for a in list(watcher.alerts)[:50]
    ]})

# ── 多Agent框架 ──
@app.route("/api/framework/status")
def fw_status():
    """多Agent框架状态"""
    if hasattr(_brain, 'framework') and _brain.framework:
        return jsonify(_brain.framework.get_system_status())
    return jsonify({"error": "多Agent框架未初始化"}), 503

@app.route("/api/framework/agents")
def fw_agents():
    """列出所有Agent"""
    if hasattr(_brain, 'framework') and _brain.framework:
        fw = _brain.framework
        agents = {}
        for name, agent in fw.router.agents.items():
            agents[name] = agent.get_context()
        return jsonify({"router": fw.router.name, "agents": agents, "total_caps": sum(len(a.capabilities) for a in fw.router.agents.values())})
    return jsonify({"error": "多Agent框架未初始化"}), 503

@app.route("/api/framework/context")
def fw_context():
    """共享上下文 — 所有Agent全局状态"""
    if hasattr(_brain, 'framework') and _brain.framework:
        ctx = _brain.framework.get_shared_context()
        return jsonify(ctx)
    return jsonify({"error": "多Agent框架未初始化"}), 503

# ── 自主AI大脑 ──
@app.route("/api/brain/status")
def br_status():
    return jsonify(_brain.get_status())

@app.route("/api/brain/start", methods=["POST"])
def br_start():
    _brain.trader = trader
    _brain.watcher = watcher
    _brain.llm = free_llm.a
    _brain.account = account
    _brain.desktop_ctl = desktop_ctl
    return jsonify(_brain.start())

@app.route("/api/brain/stop", methods=["POST"])
def br_stop():
    return jsonify(_brain.stop())

@app.route("/api/brain/context")
def br_context():
    return jsonify(list(_brain.context)[:20])


# ── 守夜人Agent API ──
@app.route("/api/watcher_agent/status")
def wa_status():
    """守夜人Agent状态 — 独立第二Agent"""
    try:
        from gbt.watcher_agent import get_watcher_agent
        wa = get_watcher_agent()
        return jsonify(wa.get_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watcher_agent/heartbeat", methods=["POST"])
def wa_heartbeat():
    """手动触发守夜人心跳"""
    try:
        from gbt.watcher_agent import get_watcher_agent
        wa = get_watcher_agent()
        result = wa.heartbeat()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── A股操盘 API ──
@app.route("/api/trader/status")
def trs():
    """操盘手状态"""
    return jsonify(trader.get_status())

@app.route("/api/trader/quotes", methods=["POST"])
def trq():
    """获取自选池行情"""
    d = request.json or {}
    codes = d.get("codes", [])
    if codes:
        data = trader.fetch_quote(codes)
    else:
        data = trader.fetch_watchlist()
    quotes = {}
    for k, v in data.items():
        quotes[k] = {"code": v.code, "name": v.name, "price": v.price,
                      "change": v.change, "change_pct": v.change_pct,
                      "prev_close": v.prev_close, "open": v.open,
                      "high": v.high, "low": v.low, "volume": v.volume,
                      "amount": v.amount, "time": v.time}
    return jsonify({"quotes": quotes})

@app.route("/api/trader/scan", methods=["POST"])
def tr_scan():
    """AI全市场扫描生成交易信号"""
    if not trader.llm and llm.a:
        trader.llm = free_llm.a
    signals = trader.scan_market()
    return jsonify({"signals": [
        {"code": s.code, "name": s.name, "action": s.action,
         "price": s.price, "confidence": s.confidence,
         "reason": s.reason, "strategy": s.strategy, "time": s.time}
        for s in signals[:30]
    ]})

@app.route("/api/trader/analyze", methods=["POST"])
def tr_analyze():
    """AI分析单只股票"""
    d = request.json or {}
    code = d.get("code", "")
    if not code:
        return jsonify({"ok": False, "error": "缺少股票代码"})
    if not trader.llm and llm.a:
        trader.llm = free_llm.a
    quotes = trader.fetch_quote([code])
    if code not in quotes:
        return jsonify({"ok": False, "error": f"无法获取 {code} 行情"})
    sig = trader.analyze_with_ai(code, quotes[code])
    return jsonify({"ok": True, "signal": {
        "code": sig.code, "name": sig.name, "action": sig.action,
        "price": sig.price, "confidence": sig.confidence,
        "reason": sig.reason, "strategy": sig.strategy
    }})

@app.route("/api/trader/search", methods=["POST"])
def tr_search():
    """搜索股票"""
    d = request.json or {}
    kw = d.get("keyword", "")
    results = trader.search_stock(kw)
    return jsonify({"results": results})

@app.route("/api/trader/trade", methods=["POST"])
def tr_trade():
    """执行交易"""
    d = request.json or {}
    code = d.get("code", "")
    action = d.get("action", "")
    shares = d.get("shares", 100)
    price = d.get("price", None)
    if not code or action not in ("buy", "sell"):
        return jsonify({"ok": False, "error": "参数错误: code + buy/sell"})
    return jsonify(trader.execute_trade(code, action, shares, price))

@app.route("/api/trader/autotrade", methods=["POST"])
def tr_autotrade():
    """开关自主交易"""
    d = request.json or {}
    enabled = d.get("enabled", True)
    trader.auto_trade = enabled
    if enabled:
        trader.start_autonomous()
    else:
        trader.stop_autonomous()
    return jsonify({"ok": True, "auto_trade": trader.auto_trade,
                    "msg": "自主交易已开启 — AI自动扫描+执行!" if trader.auto_trade else "自主交易已停止"})

@app.route("/api/trader/autonomous/start", methods=["POST"])
def tr_auto_start():
    """启动自主交易循环"""
    return jsonify(trader.start_autonomous())

@app.route("/api/trader/autonomous/stop", methods=["POST"])
def tr_auto_stop():
    """停止自主交易循环"""
    return jsonify(trader.stop_autonomous())

@app.route("/api/trader/platform", methods=["POST"])
def tr_platform():
    """打开交易平台"""
    d = request.json or {}
    name = d.get("platform", "东方财富")
    return jsonify(trader.open_platform(name))

@app.route("/api/trader/position", methods=["POST"])
def tr_position():
    """管理持仓"""
    d = request.json or {}
    act = d.get("action", "list")
    if act == "add":
        trader.add_position(d.get("code",""), d.get("name",""), d.get("shares",0), d.get("cost",0))
        return jsonify({"ok": True})
    elif act == "remove":
        trader.remove_position(d.get("code",""))
        return jsonify({"ok": True})
    return jsonify(trader.get_status())

@app.route("/api/trader/pipeline", methods=["POST"])
def tr_pipeline():
    """运行完整6阶段交易流水线"""
    d = request.json or {}
    code = d.get("code", "")
    if not code:
        return jsonify({"ok": False, "error": "缺少股票代码"})
    if not trader.llm and llm.a:
        trader.llm = free_llm.a
    session = trader.run_full_pipeline(code)
    return jsonify({"ok": True, "session": session.to_dict()})

@app.route("/api/trader/sessions")
def tr_sessions():
    """获取交易会话历史"""
    return jsonify({"sessions": [s.to_dict() for s in list(trader.sessions)[:20]]})

@app.route("/api/trader/session/<sid>")
def tr_session(sid):
    """获取单个交易会话详情"""
    for s in trader.sessions:
        if s.id == sid:
            return jsonify({"ok": True, "session": s.to_dict()})
    return jsonify({"ok": False, "error": "会话不存在"})

@app.route("/api/trader/stockpage", methods=["POST"])
def tr_stockpage():
    """打开股票详情页"""
    d = request.json or {}
    code = d.get("code", "")
    if not code:
        return jsonify({"ok": False, "error": "缺少代码"})
    return jsonify(trader.open_stock_page(code))

@app.route("/api/trader/kline", methods=["POST"])
def tr_kline():
    """获取K线数据"""
    d = request.json or {}
    code = d.get("code", "")
    scale = d.get("scale", 240)
    datalen = d.get("datalen", 30)
    if not code:
        return jsonify({"ok": False, "error": "缺少代码"})
    return jsonify(trader.fetch_kline(code, scale, datalen))

@app.route("/api/trader/strategy", methods=["POST"])
def tr_strategy():
    """多策略分析"""
    d = request.json or {}
    code = d.get("code", "")
    if not code:
        return jsonify({"ok": False, "error": "缺少代码"})
    try:
        from gbt.strategies import strategy as se
        kline = trader.fetch_kline(code, 240, 30)
        if not kline.get("ok") or len(kline.get("closes",[])) < 10:
            return jsonify({"ok": False, "error": "K线数据不足"})
        result = se.analyze(kline.get("closes", []), kline.get("highs"),
                           kline.get("lows"), kline.get("volumes"))
        return jsonify({"ok": True, "code": code, "strategy": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/trader/tech", methods=["POST"])
def tr_tech():
    """技术分析"""
    d = request.json or {}
    code = d.get("code", "")
    if not code:
        return jsonify({"ok": False, "error": "缺少代码"})
    quote = trader.fetch_quote([code])
    if code not in quote:
        return jsonify({"ok": False, "error": f"获取行情失败: {code}"})
    q = quote[code]
    try:
        from gbt.tech_analysis import FullAnalysis
        kline = trader.fetch_kline(code, 240, 30)
        if kline.get("ok") and len(kline.get("closes",[])) >= 20:
            ta = FullAnalysis(kline.get("closes", [q.price]*20), kline.get("highs"),
                             kline.get("lows"), kline.get("volumes"),
                             name=q.name, code=code)
        else:
            ta = FullAnalysis([q.price]*20, name=q.name, code=code)
        return jsonify({"ok": True, "code": code, "name": q.name, "quote": {
            "price": q.price, "change": q.change, "change_pct": q.change_pct,
            "open": q.open, "high": q.high, "low": q.low
        }, "analysis": ta, "kline": {"closes": kline.get("closes", [])}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/risk/check", methods=["POST"])
def risk_check():
    """风控审批"""
    d = request.json or {}
    try:
        from gbt.risk_ctrl import risk_mgr
        sig_type = type("Signal", (), {"action": d.get("action","buy"), "code": d.get("code",""),
            "price": d.get("price",0), "confidence": d.get("confidence",0), "reason": ""})()
        approval = risk_mgr.approve_trade(sig_type, trader.positions)
        pos_check = risk_mgr.check_position_size(d.get("price",0))
        return jsonify({
            "ok": True,
            "approval": approval,
            "position": pos_check,
            "daily": risk_mgr.check_daily_limit(),
            "config": {
                "total_capital": risk_mgr.total_capital,
                "stop_loss_pct": risk_mgr.stop_loss_pct,
                "stop_profit_pct": risk_mgr.stop_profit_pct,
                "max_single_pct": risk_mgr.max_single_pct,
                "max_daily_loss_pct": risk_mgr.max_daily_loss_pct
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/risk/config", methods=["POST"])
def risk_config():
    """更新风控参数"""
    d = request.json or {}
    try:
        from gbt.risk_ctrl import risk_mgr
        for k in ["stop_loss_pct", "stop_profit_pct", "trailing_stop_pct",
                  "max_single_pct", "max_total_pct", "max_daily_trades", "max_daily_loss_pct"]:
            if k in d:
                setattr(risk_mgr, k, d[k])
        if "total_capital" in d:
            risk_mgr.total_capital = d["total_capital"]
        return jsonify({"ok": True, "config": {
            "total_capital": risk_mgr.total_capital,
            "stop_loss_pct": risk_mgr.stop_loss_pct,
            "stop_profit_pct": risk_mgr.stop_profit_pct,
            "max_single_pct": risk_mgr.max_single_pct
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# ── 账户 API ──
@app.route("/api/account")
def acct_status():
    """账户总览"""
    prices = {}
    try:
        for code in account.positions:
            q = trader.fetch_quote([code])
            if code in q:
                prices[code] = q[code].price
    except: pass
    pnl = account.get_pnl(prices)
    positions = account.get_positions_with_value(prices)
    return jsonify({
        "ok": True,
        "account": {
            "cash": account.cash,
            "equity": pnl["equity"],
            "pnl": pnl["pnl"],
            "pnl_pct": pnl["pnl_pct"],
            "total_trades": pnl["total_trades"],
            "win_rate": pnl["win_rate"],
            "daily_pnl": pnl["daily_pnl"]
        },
        "positions": [{"code": c, **p} for c, p in positions.items()],
        "recent_log": [dict(e) for e in list(account.trade_log)[:10]]
    })

@app.route("/api/account/buy", methods=["POST"])
def acct_buy():
    """模拟买入"""
    d = request.json or {}
    return jsonify(account.buy(d.get("code",""), d.get("name",""),
                                d.get("shares", 100), d.get("price", 0)))

@app.route("/api/account/sell", methods=["POST"])
def acct_sell():
    """模拟卖出"""
    d = request.json or {}
    return jsonify(account.sell(d.get("code",""), d.get("shares", 100), d.get("price", 0)))

# ── 设置 API ──
@app.route("/api/settings")
def get_settings():
    """获取所有配置"""
    risk_cfg = {}
    try:
        from gbt.risk_ctrl import risk_mgr
        risk_cfg = {
            "stop_loss_pct": risk_mgr.stop_loss_pct,
            "stop_profit_pct": risk_mgr.stop_profit_pct,
            "trailing_stop_pct": risk_mgr.trailing_stop_pct,
            "max_single_pct": risk_mgr.max_single_pct,
            "max_total_pct": risk_mgr.max_total_pct,
            "max_daily_trades": risk_mgr.max_daily_trades,
            "max_daily_loss_pct": risk_mgr.max_daily_loss_pct,
            "total_capital": risk_mgr.total_capital
        }
    except: pass
    return jsonify({
        "ok": True,
        "trader": {
            "auto_trade": trader.auto_trade,
            "confidence_threshold": trader.confidence_threshold,
            "scan_interval": trader.scan_interval,
            "watchlist": list(trader.watchlist.keys())
        },
        "risk": risk_cfg,
        "account": account.get_config()
    })

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """更新配置"""
    d = request.json or {}
    ch = []
    if "trader" in d:
        td = d["trader"]
        for k in ["auto_trade", "confidence_threshold", "scan_interval"]:
            if k in td:
                setattr(trader, k, td[k])
                ch.append(f"trader.{k}={td[k]}")
    if "risk" in d:
        try:
            from gbt.risk_ctrl import risk_mgr
            for k, v in d["risk"].items():
                if hasattr(risk_mgr, k):
                    setattr(risk_mgr, k, v)
                    ch.append(f"risk.{k}={v}")
        except: pass
    if "watchlist_add" in d:
        for item in d["watchlist_add"]:
            code = item.get("code", "")
            name = item.get("name", code)
            if code:
                trader.watchlist[code] = name
                ch.append(f"+{code} {name}")
    if "watchlist_remove" in d:
        for code in d["watchlist_remove"]:
            if code in trader.watchlist:
                del trader.watchlist[code]
                ch.append(f"-{code}")
    return jsonify({"ok": True, "changes": ch})

@app.route("/api/trader/journal")
def tr_journal():
    """交易日志"""
    entries = []
    for sig in list(trader.signals)[:50]:
        entries.append({
            "time": sig.time,
            "code": sig.code,
            "name": sig.name,
            "action": sig.action,
            "price": sig.price,
            "confidence": sig.confidence,
            "reason": sig.reason
        })
    for sess in list(trader.sessions)[:20]:
        entries.append({
            "time": sess.created_at,
            "code": sess.code,
            "name": sess.name,
            "action": sess.executed and ("executed" if sess.status == "done" else sess.status) or "skipped",
            "session_id": sess.id,
            "status": sess.status,
            "steps": len(sess.steps)
        })
    entries.sort(key=lambda e: e.get("time", ""), reverse=True)
    return jsonify({"ok": True, "journal": entries[:50]})

@app.route("/api/trader/notify", methods=["POST"])
def tr_notify():
    """发送Windows通知"""
    d = request.json or {}
    return jsonify(trader.send_notification(
        d.get("title", "GBT操盘手"),
        d.get("message", "")
    ))

@app.route("/api/trader/steps")
def tr_steps():
    """获取浏览器自动化步骤模板"""
    platform = request.args.get("platform", "东方财富交易")
    return jsonify({"platform": platform, "steps": trader.BROWSER_STEPS.get(platform, [])})


# ── 桌面操控 API ──
@app.route("/api/desktop/type", methods=["POST"])
def dc_type():
    d = request.json or {}
    return jsonify(desktop_ctl.type_text(d.get("text", ""), d.get("interval", 0.05)))

@app.route("/api/desktop/click", methods=["POST"])
def dc_click():
    d = request.json or {}
    return jsonify(desktop_ctl.click(d.get("x"), d.get("y"), d.get("button", "left")))

@app.route("/api/desktop/hotkey", methods=["POST"])
def dc_hotkey():
    d = request.json or {}
    return jsonify(desktop_ctl.hotkey(*d.get("keys", ["ctrl", "v"])))

@app.route("/api/desktop/paste", methods=["POST"])
def dc_paste():
    d = request.json or {}
    return jsonify(desktop_ctl.paste_text(d.get("text", "")))

@app.route("/api/desktop/focus", methods=["POST"])
def dc_focus():
    d = request.json or {}
    return jsonify(desktop_ctl.focus_window(d.get("title", "")))

@app.route("/api/desktop/trade-flow", methods=["POST"])
def dc_trade_flow():
    """完整交易平台操作流程"""
    d = request.json or {}
    return jsonify(desktop_ctl.trade_platform_flow(
        platform=d.get("platform", "东方财富交易"),
        code=d.get("code", ""),
        action=d.get("action", "buy"),
        shares=d.get("shares", 100),
        price=d.get("price", 0)
    ))

# ── 仪表盘 API ──
@app.route("/api/dashboard")
def dashboard():
    """首页仪表盘总览"""
    # 系统状态
    import ctypes
    free = ctypes.c_uint64(); total = ctypes.c_uint64(); tfree = ctypes.c_uint64()
    ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\", ctypes.byref(free), ctypes.byref(total), ctypes.byref(tfree))
    disk_pct = round((total.value - free.value) / total.value * 100, 1)
    
    # 守夜人
    ws = watcher.get_status()
    monitors_ok = sum(1 for v in ws.get("monitors", {}).values() if v.get("status") == "ok")
    monitors_total = len(ws.get("monitors", {}))
    alerts_count = len(ws.get("recent_alerts", []))
    
    # 操盘手
    ts = trader.get_status()
    
    # MCP
    mcp_count = len(get_mcp().list_servers())
    
    # 连接器
    reg = get_connectors()
    all_conns = reg.list_all()
    connected = sum(1 for c in all_conns if c.get("status") == "connected")
    
    return jsonify({
        "llm": llm.prov.upper() if llm.prov else "Demo",
        "model": llm.model or "N/A",
        "mcp_servers": mcp_count,
        "connectors": {"connected": connected, "total": len(all_conns)},
        "watcher": {
            "running": ws["running"],
            "monitors_ok": monitors_ok,
            "monitors_total": monitors_total,
            "alerts": alerts_count,
            "auto_fix": ws["auto_fix"]
        },
        "trader": {
            "auto_trade": ts["auto_trade"],
            "running": ts.get("running", False),
            "watchlist": ts["watchlist_count"],
            "positions": len(ts["positions"]),
            "signals": len(ts["recent_signals"]),
            "pnl": ts["pnl"]
        },
        "system": {"disk_free_pct": round(100 - disk_pct, 1)}
    })

# ── 回测API ──
from gbt.backtest import BacktestEngine
_backtester = BacktestEngine()

@app.route("/api/backtest", methods=["POST"])
def run_backtest():
    """运行回测: {code, scale(默认240), datalen(默认120)}"""
    data = request.get_json(silent=True) or {}
    code = data.get("code", "sh600519")
    scale = data.get("scale", 240)
    datalen = data.get("datalen", 120)
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    params = data.get("params", {})
    
    kline = trader.fetch_kline(code, scale=scale, datalen=datalen)
    if not kline.get("ok") or kline.get("count", 0) < 30:
        return jsonify({"ok": False, "error": f"K线数据不足 ({kline.get('count',0)}条)"})
    
    engine = BacktestEngine()
    for k, v in params.items():
        if hasattr(engine, k): setattr(engine, k, v)
    
    result = engine.run_with_gbt_strategies(code, kline, start_date, end_date)
    return jsonify({"ok": True, "result": result.to_dict() if result else {}})

@app.route("/api/backtest/scan", methods=["POST"])
def scan_backtest():
    """参数扫描: {code, param_grid: {key:[vals]}, datalen}"""
    data = request.get_json(silent=True) or {}
    code = data.get("code", "sh600519")
    param_grid = data.get("param_grid", {"confidence_threshold": [40, 50, 60, 70]})
    datalen = data.get("datalen", 120)
    
    kline = trader.fetch_kline(code, scale=240, datalen=datalen)
    if not kline.get("ok") or kline.get("count", 0) < 30:
        return jsonify({"ok": False, "error": "K线数据不足"})
    
    engine = BacktestEngine()
    scan = engine.run_parameter_scan(code, kline, param_grid)
    return jsonify({"ok": True, **scan})

@app.route("/api/backtest/codes")
def backtest_codes():
    """可回测的股票列表(有K线缓存的)"""
    try:
        from gbt.database import db as _db
        with _db.conn() as c:
            rows = c.execute("SELECT DISTINCT code FROM kline_cache ORDER BY code").fetchall()
            return jsonify({"ok": True, "codes": [r[0] for r in rows]})
    except:
        return jsonify({"ok": True, "codes": list(trader.watchlist.keys())})




def launch():
    try:
        import webview as wv
        class GBTWindowApi:
            def min(self): wv.windows[0].minimize()
            def max(self):
                win=wv.windows[0]
                try:
                    if win.fullscreen: win.fullscreen=False
                    else: win.toggle_fullscreen()
                except Exception:
                    win.toggle_fullscreen()
            def move(self,x,y): wv.windows[0].move(int(x),int(y))
            def close(self): wv.windows[0].destroy()
        t=threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8877,debug=False,use_reloader=False),daemon=True)
        t.start();time.sleep(1.0)
        # 自动启动守夜人 + 操盘手
        # ── 数据库迁移 (内存 → SQLite) ──
        _db.migrate_account(account)
        _db.migrate_trader(trader)
        from gbt.risk_ctrl import risk_mgr
        _db.migrate_risk(risk_mgr)
        stats = _db.get_db_stats()
        L.info(f"🗄️ 数据库: {stats['trades']}笔交易 | {stats['signals']}个信号 | {stats['positions']}持仓 | {stats['kline_cache']}K线缓存")

        if llm.a:
            watcher.llm = free_llm.a
            trader.llm = free_llm.a
            trader.db = _db  # 注入数据库引用
            watcher.start()
            trader.start_autonomous()
            L.info("🛡️ 守夜人已自动启动")
            L.info("📊 自主交易已启动")
            # 启动自主AI大脑
            _brain.trader = trader
            _brain.watcher = watcher
            _brain.llm = free_llm.a
            _brain.account = account
            _brain.desktop_ctl = desktop_ctl
            
            # ── 智能路由器注入 ──
            import gbt.capabilities as _caps  # 触发能力注册
            from gbt.router import router as _router
            _router.set_dependency("trader", trader)
            _router.set_dependency("watcher", watcher)
            _router.set_dependency("account", account)
            _router.set_dependency("brain", _brain)
            _router.set_dependency("desktop_ctl", desktop_ctl)
            _router.set_dependency("llm", llm.a)
            _brain.router = _router
            # 注入执行协议 (7阶段)
            from gbt.protocol import protocol as _protocol
            _router.set_protocol(_protocol)
            _brain.protocol = _protocol
            L.info(f"🧭 智能路由器已注入: {len(_router.capabilities)} 项能力 + 7阶段协议")
            
            # 🚀 初始化多Agent框架 (RouterAgent + 5领域Agent)
            from gbt.agents import init_framework
            framework = init_framework(brain=_brain, trader=trader, account=account, watcher=watcher)
            _brain.framework = framework
            L.info(f"🚀 多Agent框架就绪: {len(framework.router.agents)}领域Agent + RouterAgent")
            
            _brain.start()
        time.sleep(0.5)
        L.info("Desktop window opening...");wv.create_window("GBT Pro v2.1","http://localhost:8877/?v="+str(int(time.time())),width=1200,height=720,min_size=(1000,600),js_api=GBTWindowApi());wv.start()
    except ImportError:
        L.warning("Browser mode");L.info("http://localhost:8765");app.run(host="127.0.0.1",port=8765,debug=False)

def main():
    import argparse;p=argparse.ArgumentParser();p.add_argument("--browser",action="store_true");p.add_argument("--server",action="store_true");a=p.parse_args()
    if a.server:
        L.info("Flask server mode - http://localhost:8765");app.run(host="127.0.0.1",port=8765,debug=False)
    elif a.browser:
        try:
            trader.start_autonomous()
            watcher.start()
            _brain.trader=trader;_brain.watcher=watcher;_brain.llm=llm.a;_brain.account=account;_brain.desktop_ctl=desktop_ctl
            import gbt.capabilities as _caps
            from gbt.router import router as _router
            _router.set_dependency("trader",trader);_router.set_dependency("watcher",watcher)
            _router.set_dependency("account",account);_router.set_dependency("brain",_brain)
            _router.set_dependency("desktop_ctl",desktop_ctl);_router.set_dependency("llm",llm.a)
            _brain.router=_router
            from gbt.protocol import protocol as _protocol
            _router.set_protocol(_protocol);_brain.protocol=_protocol
            from gbt.agents import init_framework
            framework=init_framework(brain=_brain,trader=trader,account=account,watcher=watcher)
            _brain.framework=framework
            _brain.start()
            L.info("Browser mode initialized")
        except Exception as e:
            L.warning(f"Init partial: {e}")
        L.info("http://localhost:8766");app.run(host="127.0.0.1",port=8766,debug=False)
    else:launch()

if __name__=="__main__":main()
