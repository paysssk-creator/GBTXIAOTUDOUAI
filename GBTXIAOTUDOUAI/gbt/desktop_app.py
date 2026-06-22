# -*- coding: utf-8 -*-
"""GBT Workstation v4 - Full Capabilities"""
import tkinter as tk
from tkinter import ttk
import os,sys,threading,time,webbrowser
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
BG0="#0a0e14";BG1="#131820";BG2="#1c2433"
FG0="#e6e8ec";FG1="#8b949e";ACC="#39d353";ACC2="#58a6ff";ERR="#f85149"

class GBT:
 def __init__(s):
  s.r=tk.Tk();s.r.title("GBT Workstation v4");s.r.geometry("1100x700")
  s.r.configure(bg=BG0);s._rev={};s._build();s._center();s._load()

 def _center(s):
  s.r.update_idletasks()
  w_=s.r.winfo_width();h_=s.r.winfo_height()
  sw=s.r.winfo_screenwidth();sh=s.r.winfo_screenheight()
  s.r.geometry(f"+{(sw-w_)//2}+{(sh-h_)//2}")

 def _build(s):
  nb=ttk.Notebook(s.r);nb.pack(fill="both",expand=True)
  sf=ttk.Style();sf.theme_use("clam")
  sf.configure("TNotebook",background=BG1,borderwidth=0)
  sf.configure("TNotebook.Tab",padding=[14,5],
                font=("Cascadia Code",9,"bold"),
                background=BG1,foreground=FG1)
  sf.map("TNotebook.Tab",background=[("selected",ACC2)],
         foreground=[("selected",FG0)])
  bar=tk.Frame(s.r,bg=BG1,height=24);bar.pack(fill="x",side="bottom")
  s.sb=tk.Label(bar,text="READY",bg=BG1,fg=ACC,
               font=("Cascadia Code",7));s.sb.pack(side="right",padx=10)
  tk.Label(bar,text="v4.0 | 7 tabs | 40 modules | github.com/paysssk-creator",
           bg=BG1,fg=FG1,font=("Cascadia Code",7)).pack(side="left",padx=10)
  s._keys_tab(nb);s._trade_tab(nb);s._desk_tab(nb)
  s._ai_tab(nb);s._sec_tab(nb);s._mcp_tab(nb);s._stat_tab(nb)
  def _keys_tab(s,nb):
   p=tk.Frame(nb,bg=BG0);nb.add(p,text="Keys");s._kf=tk.Frame(p,bg=BG0)
   s._kf.pack(fill="both",expand=True,padx=12,pady=6)
  def _load(s):
   for w in s._kf.winfo_children():w.destroy()
   from gbt.keydb import KeyDB;db=KeyDB();ok=0
   h=tk.Frame(s._kf,bg=BG0);h.pack(fill="x",pady=(0,4))
   tk.Label(h,text="API Keys",bg=BG0,fg=FG0,
            font=("Cascadia Code",11,"bold")).pack(side="left")
   im=tk.Label(h,text="Import All",bg=BG2,fg=ACC2,font=("Cascadia Code",8),
               padx=10,pady=3,cursor="hand2");im.pack(side="right")
   im.bind("<Button-1>",lambda e:s._imp())
   from gbt.keydb import FREE_TIER
   for pid,info in sorted(FREE_TIER.items(),key=lambda x:x[1]["pri"]):
    key=db.get(pid);r=tk.Frame(s._kf,bg=BG1,height=32)
    r.pack(fill="x",pady=1);r.pack_propagate(False)
    c=ACC if key else FG1
    tk.Label(r,text="*" if key else "-",bg=BG1,fg=c,font=("Cascadia Code",10),
             width=2).pack(side="left",padx=(8,0))
    tk.Label(r,text=info["name"],bg=BG1,fg=FG0,font=("Cascadia Code",10),
             width=13,anchor="w").pack(side="left",padx=4)
    pv=(key[:12]+"..."+key[-6:]) if key and len(key)>20 else ("-" if not key else key)
    tk.Label(r,text=pv,bg=BG1,fg=c,font=("Cascadia Code",9),
             width=22,anchor="w").pack(side="left",padx=4)
    tk.Label(r,text=info["free"][:24],bg=BG1,fg=FG1,
             font=("Cascadia Code",8)).pack(side="left",padx=4)
    af=tk.Frame(r,bg=BG1);af.pack(side="right",padx=4)
    if key:
     for t,cb in[("Copy",lambda k=key,p=pid:s._cp(k,p)),
                 ("Test",lambda p=pid:s._tk(p))]:
      xb=tk.Label(af,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",7),
                  padx=5,pady=1,cursor="hand2");xb.pack(side="left",padx=1)
      xb.bind("<Button-1>",lambda e,c=cb:c())
     r.bind("<Button-1>",lambda e,r=r,k=key:s._tg(r,k));ok+=1
    else:
     xb=tk.Label(af,text="Reg",bg=BG2,fg=ACC2,font=("Cascadia Code",7),
                 padx=5,pady=1,cursor="hand2");xb.pack(side="left",padx=1)
     url=info.get("url","")
     xb.bind("<Button-1>",lambda e,u=url:webbrowser.open(u) if u else None)
   s.sb.config(text=f"{ok}/{len(FREE_TIER)} keys")
  def _cp(s,k,pid):s.r.clipboard_clear();s.r.clipboard_append(k)
  def _tg(s,row,key):
   for c in row.winfo_children():
    if isinstance(c,tk.Label):
     t=c.cget("text")
     if len(t)>15 and"..."in t:c.config(text=key)
     elif key and key[:10]in t:c.config(text=key[:12]+"..."+key[-6:])
  def _tk(s,pid):
   s.sb.config(text=f"Testing {pid}...")
   def do():
    try:
     from gbt.keydb import KeyDB;key=KeyDB().get(pid)
    except:key=None
    if key:
     try:
      os.environ[(pid.upper()+"_API_KEY")]=key
      from gbt.llm import GBTLLM
      GBTLLM(provider=pid,timeout=12,max_tokens=10).invoke(
       [{"role":"user","content":"ok"}])
      s.r.after(0,lambda:s.sb.config(text=f"OK {pid}"))
     except Exception as e:
      s.r.after(0,lambda:s.sb.config(text=f"FAIL {pid}"))
    else:
     s.r.after(0,lambda:s.sb.config(text="NO KEY"))
   threading.Thread(target=do,daemon=True).start()
  def _imp(s):
   try:
    from gbt.keydb import auto_import;auto_import();s._load()
    s.sb.config(text="IMPORTED")
   except Exception as e:s.sb.config(text=str(e)[:30])

 def _trade_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Trade")
  l=tk.Frame(p,bg=BG0);l.pack(side="left",fill="both",expand=True,padx=12,pady=8)
  tk.Label(l,text="Trading Console",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w")
  inf=tk.Frame(l,bg=BG2);inf.pack(fill="x",pady=(4,2))
  s._ci=tk.Text(inf,height=3,bg=BG2,fg=FG0,font=("Cascadia Code",10),
   insertbackground=ACC,relief="flat",padx=8,pady=6)
  s._ci.pack(side="left",fill="x",expand=True)
  s._ci.insert("1.0","Analyze 600519, buy 100 shares if bullish")
  bc=tk.Frame(inf,bg=BG2);bc.pack(side="right",fill="y",padx=4,pady=4)
  g=tk.Label(bc,text="EXECUTE",bg=ACC,fg=BG0,
   font=("Cascadia Code",9,"bold"),padx=12,pady=6,cursor="hand2")
  g.pack();g.bind("<Button-1>",lambda e:s._exec())
  st=tk.Label(bc,text="STOP",bg=ERR,fg="#fff",font=("Cascadia Code",9),
   padx=12,pady=2,cursor="hand2")
  st.pack(pady=(2,0));st.bind("<Button-1>",lambda e:setattr(s,"_stop",True))
  qf=tk.Frame(l,bg=BG0);qf.pack(fill="x",pady=2)
  for t,cmd in[("600519","Analyze 600519"),("K-line","Show K-line"),
   ("Buy 100","Buy 100"),("Sell","Sell all"),("Strategies","List strategies")]:
   c=tk.Label(qf,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",9),
    padx=6,pady=1,cursor="hand2");c.pack(side="left",padx=1)
   c.bind("<Button-1>",lambda e,cmd=cmd:[s._ci.delete("1.0","end"),
    s._ci.insert("1.0",cmd)])
  tk.Label(l,text="OUTPUT",bg=BG0,fg=FG1,
   font=("Cascadia Code",8,"bold")).pack(anchor="w",pady=(6,1))
  s._co=tk.Text(l,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._co.pack(fill="both",expand=True)
 def _exec(s):
  task=s._ci.get("1.0","end-1c").strip()
  if not task:return
  s._stop=False;s._log("TASK: "+task);s.sb.config(text="RUNNING")
  def loop():
   try:
    from gbt.autopilot import Autopilot,compress_for_vision,ScreenState
    from gbt.llm import GBTLLM;from PIL import ImageGrab
    llm=GBTLLM(provider="zhipu",model="glm-4v",timeout=60,max_tokens=300)
    ap=Autopilot(llm_provider=llm)
    for turn in range(1,4):
     if s._stop:break
     s.r.after(0,lambda t=turn:s._log(f"[T{t}] screenshot..."))
     img=ImageGrab.grab();b64=compress_for_vision(img,480)
     st=ScreenState(image=img,base64=b64,timestamp=time.time())
     s.r.after(0,lambda:s._log("[T] GLM-4V analyzing..."))
     for a in ap.analyze(st,task):
      if s._stop:break
      s.r.after(0,lambda a=a:s._log(f"  [{a.action_type}] {a.reasoning[:100]}"))
      try:ap.execute(a)
      except Exception as e:s.r.after(0,lambda e=e:s._log(f"  ERR: {e}"))
    s.r.after(0,lambda:s._log("DONE"))
    s.r.after(0,lambda:s.sb.config(text="READY"))
   except Exception as e:
    s.r.after(0,lambda:s._log(f"FAIL: {e}"))
    s.r.after(0,lambda:s.sb.config(text="ERROR"))
  threading.Thread(target=loop,daemon=True).start()
 def _log(s,msg):
  s._co.config(state="normal");s._co.insert("end",msg+"\n")
  s._co.see("end");s._co.config(state="disabled")

 def _desk_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Desktop")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("Screen",lambda:s._desk("screen")),("Snap",lambda:s._desk("snap")),
   ("Mouse",lambda:s._desk("mouse")),("Process",lambda:s._desk("proc")),
   ("OCR",lambda:s._desk("ocr")),("Voice",lambda:s._desk("mic")),
   ("TTS",lambda:s._desk("tts")),("BT Scan",lambda:s._desk("bt"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="Desktop Control Center",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._dc=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._dc.pack(fill="both",expand=True,padx=12,pady=(2,10))

 def _desk(s,cmd):
  s._dc.config(state="normal");s._dc.delete("1.0","end")
  s._dc.insert("end",f"[{cmd}] running...\n")
  try:
   from gbt.winctl import WindowsController;wc=WindowsController()
   if cmd=="screen":r=wc.screenshot();s._dc.insert("end",f"Screenshot: {type(r)}\n")
   elif cmd=="snap":r=wc.screenshot();s._dc.insert("end","Snap taken\n")
   elif cmd=="mouse":r=wc.mouse_position();s._dc.insert("end",f"Mouse: {r}\n")
   elif cmd=="proc":r=wc.list_processes();s._dc.insert("end",str(r)[:400]+"\n")
   elif cmd=="ocr":
    try:from gbt.ocr import screen_to_text;r=screen_to_text();s._dc.insert("end",f"OCR: {str(r)[:200]}\n")
    except Exception as e:s._dc.insert("end",f"OCR ERR: {e}\n")
   elif cmd=="mic":
    try:import speech_recognition as sr;r=sr.Recognizer();s._dc.insert("end","Mic: ready\n")
    except Exception as e:s._dc.insert("end",f"Mic ERR: {e}\n")
   elif cmd=="tts":
    try:import pyttsx3;e=pyttsx3.init();s._dc.insert("end","TTS: ready\n")
    except Exception as e:s._dc.insert("end",f"TTS ERR: {e}\n")
   elif cmd=="bt":
    try:import bleak;s._dc.insert("end","BT: bleak ready\n")
    except Exception as e:s._dc.insert("end",f"BT ERR: {e}\n")
  except Exception as e:
   s._dc.insert("end",f"ERR: {e}\n")
  s._dc.config(state="disabled")

 def _ai_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="AI Engine")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("LLM",lambda:s._ai("llm")),("Metrics",lambda:s._ai("metrics")),
   ("Reasoner",lambda:s._ai("reason")),("Memory",lambda:s._ai("memory")),
   ("Knowledge",lambda:s._ai("kb")),("Router",lambda:s._ai("router"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="AI Engine Diagnostics",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._ao=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._ao.pack(fill="both",expand=True,padx=12,pady=(2,10))
 def _ai(s,cmd):
  s._ao.config(state="normal");s._ao.delete("1.0","end")
  try:
   if cmd=="llm":
    s._ao.insert("end","LLM: zhipu+deepseek+openrouter ready\n")
    from gbt.providers import PROVIDERS
    for pid,cfg in list(PROVIDERS.items())[:8]:
     s._ao.insert("end",f"  {cfg['name']}: {cfg.get('pricing','')}\n")
   elif cmd=="metrics":
    from gbt.llm_metrics import get_metrics
    s._ao.insert("end",str(get_metrics())[:500])
   elif cmd=="reason":
    from gbt.reasoner import Reasoner;s._ao.insert("end","Reasoner: 8 modes\n")
   elif cmd=="memory":
    from gbt.memory import Memory;s._ao.insert("end","Memory: working+episodic+persistent\n")
   elif cmd=="kb":
    from gbt.knowledge_base import get_system_prompt;s._ao.insert("end","Knowledge Base loaded\n")
   elif cmd=="router":
    from gbt.router import Router;s._ao.insert("end","Router: model routing ready\n")
  except Exception as e:
   s._ao.insert("end",f"ERR: {e}\n")
  s._ao.config(state="disabled")

 def _sec_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Security")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("Evolve",lambda:s._sec("evolve")),
   ("Guard",lambda:s._sec("guard")),("Mirror",lambda:s._sec("mirror")),
   ("Watcher",lambda:s._sec("watcher")),
   ("Risk",lambda:s._sec("risk"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="Security Center",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._se=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._se.pack(fill="both",expand=True,padx=12,pady=(2,10))
 def _sec(s,cmd):
  s._se.config(state="normal");s._se.delete("1.0","end")
  try:
   if cmd=="evolve":
    from gbt.evolve import Evolve;s._se.insert("end","Evolve: 6-step self-evolution\n")
   elif cmd=="guard":
    from gbt.guard import Guard;s._se.insert("end","Guard: pre-action full-scan\n")
   elif cmd=="mirror":
    from gbt.mirror import Mirror;s._se.insert("end","Mirror: sandbox-verify-deploy\n")
   elif cmd=="watcher":
    from gbt.watcher import Watcher;s._se.insert("end","Watcher: 24/7 monitor\n")
   elif cmd=="risk":
    from gbt.risk_ctrl import RiskCtrl;s._se.insert("end","RiskCtrl: position limits\n")
  except Exception as e:
   s._se.insert("end",f"ERR: {e}\n")
  s._se.config(state="disabled")

 def _mcp_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="MCP")
  tk.Label(p,text="MCP Server Hub",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(10,4))
  s._mt=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._mt.pack(fill="both",expand=True,padx=12,pady=(8,10))
  s._mcp_refresh()
 def _mcp_refresh(s):
  s._mt.config(state="normal");s._mt.delete("1.0","end")
  try:
   from gbt.mcp import MCPServer
   servers=["scanner","audit","auto-fix","bounty-hunter","cloud-llm",
    "desktop-control","email-watcher","global-memory",
    "intelligent-scheduler","memory","mcp-router","mirror-deploy",
    "rustdesk","self-evolve","stress-test","halo-cms",
    "deepseek-analyzer"]
   s._mt.insert("end",f"MCP Servers ({len(servers)}):\n\n")
   for i,sv in enumerate(servers,1):
    s._mt.insert("end",f"  {i:2d}. {sv}\n")
  except Exception as e:
   s._mt.insert("end",f"ERR: {e}\n")
  s._mt.config(state="disabled")

 def _stat_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Status")
  tk.Label(p,text="System Status",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(10,4))
  s._st=tk.Text(p,bg=BG1,fg=FG0,font=("Cascadia Code",10),
   state="disabled",relief="flat",padx=14,pady=10)
  s._st.pack(fill="both",expand=True,padx=12,pady=(8,10))
  s._refresh()
 def _refresh(s):
  s._st.config(state="normal");s._st.delete("1.0","end")
  L=["="*50," GBT Workstation v4.0 - Full Diagnostics","="*50]
  try:
   from gbt.keydb import KeyDB;db=KeyDB();av=db.available()
   L.append(f" Keys: {len(av)}/{len(db.FREE_TIER)} configured")
   for pid,name,_ in av[:6]:
    k=db.get(pid)
    L.append(f"   {name}: {k[:14]}..." if k else f"   {name}: (none)")
  except Exception as e:L.append(f" Keys: {e}")
  try:from gbt.llm import GBTLLM;L.append(" LLM: Ready (zhipu+deepseek)")
  except:L.append(" LLM: Not loaded")
  try:from gbt.autopilot import Autopilot;L.append(" Autopilot: Ready")
  except:L.append(" Autopilot: Not loaded")
  try:from gbt.winctl import WindowsController;L.append(" WinCtl: Ready")
  except:L.append(" WinCtl: Not loaded")
  try:from gbt.evolve import Evolve;L.append(" Evolve: Ready")
  except:L.append(" Evolve: Not loaded")
  try:from gbt.strategies import get_strategy;L.append(" Strategies: Ready")
  except:L.append(" Strategies: Not loaded")
  try:from gbt.trader import Trader;L.append(" Trader: Ready")
  except:L.append(" Trader: Not loaded")
  try:from gbt.backtest import Backtest;L.append(" Backtest: Ready")
  except:L.append(" Backtest: Not loaded")
  try:from gbt.mcp import MCPServer;L.append(" MCP: Ready (17 servers)")
  except:L.append(" MCP: Not loaded")
  try:from gbt.reasoner import Reasoner;L.append(" Reasoner: Ready (8 modes)")
  except:L.append(" Reasoner: Not loaded")
  try:from gbt.ocr import screen_to_text;L.append(" OCR: Ready")
  except:L.append(" OCR: Not loaded")
  try:from gbt.memory import Memory;L.append(" Memory: Ready")
  except:L.append(" Memory: Not loaded")
  L.append("="*50)
  L.append(f" Python {sys.version.split()[0]} | TK {tk.TkVersion}")
  L.append(" github.com/paysssk-creator/GBTXIAOTUDOUAI")
  s._st.insert("1.0","\n".join(L));s._st.config(state="disabled")

 def run_app():GBT().r.mainloop()
 if __name__=="__main__":run_app()
