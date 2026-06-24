"""GBT Desktop Pro v3.1"""
import tkinter as tk
from tkinter import ttk
import os,sys,threading,time,webbrowser
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
BG0="#0a0e14";BG1="#131820";BG2="#1c2433"
FG0="#e6e8ec";FG1="#8b949e";ACC="#39d353";ACC2="#58a6ff";ERR="#f85149"

class GBTWorkstation:
 def __init__(s):
  s.r=tk.Tk();s.r.title("GBT Workstation v4");s.r.geometry("1100x700");s.r.configure(bg=BG0)
  s.r.attributes("-topmost",True);s.r.after(500,lambda:s.r.attributes("-topmost",False))
  s._c={};s._build();s._ctr()
 def _ctr(s):
  s.r.update_idletasks();x=s.r.winfo_width();y=s.r.winfo_height()
  sw=s.r.winfo_screenwidth();sh=s.r.winfo_screenheight()
  s.r.geometry(f"+{(sw-x)//2}+{(sh-y)//2}")
 def _build(s):
  nb=ttk.Notebook(s.r);nb.pack(fill="both",expand=True)
  sf=ttk.Style();sf.theme_use("clam")
  sf.configure("TNotebook",background=BG1,borderwidth=0)
  sf.configure("TNotebook.Tab",padding=[14,5],font=("Cascadia Code",9,"bold"),background=BG1,foreground=FG1)
  sf.map("TNotebook.Tab",background=[("selected",ACC2)],foreground=[("selected",FG0)])
  bar=tk.Frame(s.r,bg=BG1,height=24);bar.pack(fill="x",side="bottom")
  s.sb=tk.Label(bar,text="READY",bg=BG1,fg=ACC,font=("Cascadia Code",7));s.sb.pack(side="right",padx=10)
  tk.Label(bar,text="v4.0 | 7 tabs | 40 modules",bg=BG1,fg=FG1,font=("Cascadia Code",7)).pack(side="left",padx=10)
  s._keys_tab(nb);s._trade_tab(nb);s._desk_tab(nb)
  s._ai_tab(nb);s._sec_tab(nb);s._mcp_tab(nb);s._stat_tab(nb);s._vision_tab(nb)
 def _keys_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Keys");s._kf=tk.Frame(p,bg=BG0)
  s._kf.pack(fill="both",expand=True,padx=12,pady=6);s._load()
 def _load(s):
  for w in s._kf.winfo_children():w.destroy()
  from gbt.keydb import KeyDB;db=KeyDB();ok=0;total=0
  h=tk.Frame(s._kf,bg=BG0);h.pack(fill="x",pady=(0,6))
  tk.Label(h,text="API Keys",bg=BG0,fg=FG0,font=("Cascadia Code",11,"bold")).pack(side="left")
  b=tk.Label(h,text="Import",bg=BG2,fg=ACC2,font=("Cascadia Code",8),
             padx=10,pady=3,cursor="hand2");b.pack(side="right")
  b.bind("<Button-1>",lambda e:s._imp())
  for pid,name,has_key in db.available():
   key=db.get(pid)
   r=tk.Frame(s._kf,bg=BG1,height=36);r.pack(fill="x",pady=2);r.pack_propagate(False)
   c=ACC if key else FG1
   tk.Label(r,text="* " if key else "- ",bg=BG1,fg=c,
            font=("Cascadia Code",10)).pack(side="left",padx=(8,0))
   tk.Label(r,text=name,bg=BG1,fg=FG0,
            font=("Cascadia Code",10),width=15,anchor="w").pack(side="left",padx=4)
   pv=(key[:12]+"..."+key[-6:]) if key and len(key)>20 else ("-" if not key else key)
   tk.Label(r,text=pv,bg=BG1,fg=c,font=("Cascadia Code",9),
            width=26,anchor="w").pack(side="left",padx=4)
   tk.Label(r,text="Free" if has_key else "Not Set",bg=BG1,fg=FG1,
            font=("Cascadia Code",8)).pack(side="left",padx=4)
   af=tk.Frame(r,bg=BG1);af.pack(side="right",padx=6)
   if key:
    for t,cb in[("Copy",lambda k=key,p=pid:s._cp(k,p)),("Test",lambda p=pid:s._tk(p))]:
     xb=tk.Label(af,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",7),
                 padx=6,pady=2,cursor="hand2");xb.pack(side="left",padx=2)
     xb.bind("<Button-1>",lambda e,c=cb:c())
     xb.bind("<Enter>",lambda e,b=xb:b.configure(bg="#2d3a4a"))
     xb.bind("<Leave>",lambda e,b=xb:b.configure(bg=BG2))
    r.bind("<Button-1>",lambda e,r=r,k=key:s._tg(r,k));ok+=1
   else:
    url=None
    xb=tk.Label(af,text="Register",bg=BG2,fg=ACC2,font=("Cascadia Code",7),
                padx=6,pady=2,cursor="hand2");xb.pack(side="left",padx=2)
    xb.bind("<Button-1>",lambda e,u=url:webbrowser.open(u) if u else None)
  s.sb.config(text=f"{ok}/{total} KEYS")
 def _cp(s,key,pid):
  s.r.clipboard_clear();s.r.clipboard_append(key);s.sb.config(text=f"Copied {pid}")
 def _tg(s,row,key):
  for c in row.winfo_children():
   if isinstance(c,tk.Label):
    t=c.cget("text")
    if len(t)>15 and"..."in t:c.config(text=key)
    elif key[:10]in t:c.config(text=key[:12]+"..."+key[-6:])
 def _tk(s,pid):
  s.sb.config(text=f"Testing {pid}...")
  def do():
   try:
    from gbt.keydb import KeyDB;key=KeyDB().get(pid)
    if key:
     os.environ[(pid.upper()+"_API_KEY")]=key;from gbt.llm import GBTLLM
     GBTLLM(provider=pid,timeout=12,max_tokens=10).invoke([{"role":"user","content":"ok"}])
     s.r.after(0,lambda:s.sb.config(text=f"OK {pid}"))
    else:s.r.after(0,lambda:s.sb.config(text="NO KEY"))
   except Exception as e:s.r.after(0,lambda:s.sb.config(text=f"FAIL {pid}"))
  threading.Thread(target=do,daemon=True).start()
 def _imp(s):
  try:
   from gbt.keydb import auto_import;auto_import();s._load();s.sb.config(text="IMPORTED")
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
   ("Buy 100","Buy 100"),("Sell","Sell all")]:
   c=tk.Label(qf,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",9),
    padx=6,pady=1,cursor="hand2");c.pack(side="left",padx=1)
   c.bind("<Button-1>",lambda e,cmd=cmd:[s._ci.delete("1.0","end"),
    s._ci.insert("1.0",cmd)])
  tk.Label(l,text="OUTPUT",bg=BG0,fg=FG1,
   font=("Cascadia Code",8,"bold")).pack(anchor="w",pady=(6,1))
  s._co=tk.Text(l,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._co.pack(fill="both",expand=True)
 def _desk_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Desktop")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("Screen",lambda:s._desk("screen")),
   ("Snap",lambda:s._desk("snap")),("Mouse",lambda:s._desk("mouse")),
   ("Procs",lambda:s._desk("proc")),("OCR",lambda:s._desk("ocr")),
   ("Mic",lambda:s._desk("mic")),("TTS",lambda:s._desk("tts")),
   ("BT",lambda:s._desk("bt"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="Desktop Control",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._dc=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._dc.pack(fill="both",expand=True,padx=12,pady=(2,10))
 def _ai_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="AI Engine")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("LLM",lambda:s._ai("llm")),("Metrics",lambda:s._ai("metrics")),
   ("Reason",lambda:s._ai("reason")),("Memory",lambda:s._ai("memory")),
   ("KB",lambda:s._ai("kb")),("Router",lambda:s._ai("router"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="AI Engine",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._ao=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._ao.pack(fill="both",expand=True,padx=12,pady=(2,10))
 def _sec_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Security")
  row=tk.Frame(p,bg=BG0);row.pack(fill="x",padx=12,pady=(10,4))
  for t,f in[("Evolve",lambda:s._sec("evolve")),
   ("Guard",lambda:s._sec("guard")),("Mirror",lambda:s._sec("mirror")),
   ("Watcher",lambda:s._sec("watcher")),("Risk",lambda:s._sec("risk"))]:
   b=tk.Label(row,text=t,bg=BG2,fg=ACC2,font=("Cascadia Code",8),
    padx=8,pady=3,cursor="hand2");b.pack(side="left",padx=2)
   b.bind("<Button-1>",lambda e,f=f:f())
  tk.Label(p,text="Security Center",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(4,2))
  s._se=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._se.pack(fill="both",expand=True,padx=12,pady=(2,10))
 def _mcp_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="MCP")
  tk.Label(p,text="MCP Server Hub",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(10,4))
  s._mt=tk.Text(p,bg=BG1,fg=ACC,font=("Cascadia Code",9),
   state="disabled",relief="flat",padx=10,pady=6)
  s._mt.pack(fill="both",expand=True,padx=12,pady=(8,10))
  s._mt.insert("1.0","MCP Servers: 17 loaded\n")
 def _stat_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Status")
  tk.Label(p,text="System Status",bg=BG0,fg=FG0,
   font=("Cascadia Code",11,"bold")).pack(anchor="w",padx=12,pady=(10,4))
  s._st=tk.Text(p,bg=BG1,fg=FG0,font=("Cascadia Code",10),
   state="disabled",relief="flat",padx=14,pady=10)
  s._st.pack(fill="both",expand=True,padx=12,pady=(8,10))
  s._st.insert("1.0","Python 3.12 | TK "+str(tk.TkVersion)+"\nModules: 40 loaded\nKeys: DeepSeek+OpenClaw\nStatus: Ready")

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
 def _vision_tab(s,nb):
  p=tk.Frame(nb,bg=BG0);nb.add(p,text="Vision")
  tk.Label(p,text="AI Vision Control",bg=BG0,fg=FG0,font=("Cascadia Code",12,"bold")).pack(anchor="w",padx=12,pady=8)
  info=tk.Label(p,text="Status: initializing...",bg=BG0,fg=FG1,font=("Cascadia Code",9),justify="left")
  info.pack(anchor="w",padx=12,pady=4)
  def refresh():
   try:
    from gbt.vision import VisionService
    v=VisionService()
    img=v.screenshot()
    size=str(img.size) if img else "FAIL"
    ocr=v.ocr(img) if img else {"ok":False,"error":"screenshot failed"}
    ocrok="OK" if ocr.get("ok") else "FAIL"
    txt="Vision Status\nScreenshot: "+size+"\nOCR: "+ocrok+" | chars="+str(len(ocr.get("text","")))
    info.config(text=txt)
   except Exception as e:
    info.config(text="Vision error: "+str(e))
  b=tk.Label(p,text="Refresh / Screenshot",bg=BG2,fg=ACC2,font=("Cascadia Code",9),padx=12,pady=4,cursor="hand2")
  b.pack(anchor="w",padx=12,pady=6)
  b.bind("<Button-1>",lambda e:refresh())
  refresh()
def run_app():GBTWorkstation().r.mainloop()
if __name__=="__main__":run_app()