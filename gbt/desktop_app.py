"""GBT Desktop Pro v3.1"""
import tkinter as tk
from tkinter import ttk
import os,sys,threading,time,webbrowser
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
BG0="#0a0e14";BG1="#131820";BG2="#1c2433"
FG0="#e6e8ec";FG1="#8b949e";ACC="#39d353";ACC2="#58a6ff";ERR="#f85149"

class GBTWorkstation:
 def __init__(s):
  s.r=tk.Tk();s.r.title("GBT Workstation");s.r.geometry("900x600");s.r.configure(bg=BG0)
  s._c={};s._build();s._ctr();s._load()
 def _ctr(s):
  s.r.update_idletasks();x=s.r.winfo_width();y=s.r.winfo_height()
  sw=s.r.winfo_screenwidth();sh=s.r.winfo_screenheight()
  s.r.geometry(f"+{(sw-x)//2}+{(sh-y)//2}")
 def _build(s):
  b=tk.Frame(s.r,bg=BG1,height=44);b.pack(fill="x");b.pack_propagate(False)
  tk.Label(b,text="GBT WORKSTATION",bg=BG1,fg=ACC,
           font=("Cascadia Code",14,"bold")).pack(side="left",padx=16,pady=8)
  s.sb=tk.Label(b,text="ONLINE",bg=BG1,fg=ACC,font=("Cascadia Code",9))
  s.sb.pack(side="right",padx=16,pady=8)
  s.ca=tk.Frame(s.r,bg=BG0);s.ca.pack(side="left",fill="both",expand=True)
  s._kf=tk.Frame(s.ca,bg=BG0);s._kf.pack(fill="both",expand=True,padx=16,pady=8)
  bar=tk.Frame(s.r,bg=BG1,height=22);bar.pack(fill="x",side="bottom")
  tk.Label(bar,text="GLM-4V + 11 providers | github.com/paysssk-creator",
           bg=BG1,fg=FG1,font=("Cascadia Code",7)).pack(side="left",padx=10)
 def _load(s):
  for w in s._kf.winfo_children():w.destroy()
  from gbt.keydb import KeyDB;db=KeyDB();ok=0
  h=tk.Frame(s._kf,bg=BG0);h.pack(fill="x",pady=(0,6))
  tk.Label(h,text="API Keys",bg=BG0,fg=FG0,font=("Cascadia Code",11,"bold")).pack(side="left")
  b=tk.Label(h,text="Import",bg=BG2,fg=ACC2,font=("Cascadia Code",8),
             padx=10,pady=3,cursor="hand2");b.pack(side="right")
  b.bind("<Button-1>",lambda e:s._imp())
  for pid,info in sorted(db.FREE_TIER.items(),key=lambda x:x[1]["pri"]):
   key=db.get(pid)
   r=tk.Frame(s._kf,bg=BG1,height=36);r.pack(fill="x",pady=2);r.pack_propagate(False)
   c=ACC if key else FG1
   tk.Label(r,text="* " if key else "- ",bg=BG1,fg=c,
            font=("Cascadia Code",10)).pack(side="left",padx=(8,0))
   tk.Label(r,text=info["name"],bg=BG1,fg=FG0,
            font=("Cascadia Code",10),width=15,anchor="w").pack(side="left",padx=4)
   pv=(key[:12]+"..."+key[-6:]) if key and len(key)>20 else ("-" if not key else key)
   tk.Label(r,text=pv,bg=BG1,fg=c,font=("Cascadia Code",9),
            width=26,anchor="w").pack(side="left",padx=4)
   tk.Label(r,text=info["free"][:28],bg=BG1,fg=FG1,
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
    url=info.get("url","")
    xb=tk.Label(af,text="Register",bg=BG2,fg=ACC2,font=("Cascadia Code",7),
                padx=6,pady=2,cursor="hand2");xb.pack(side="left",padx=2)
    xb.bind("<Button-1>",lambda e,u=url:webbrowser.open(u) if u else None)
  s.sb.config(text=f"{ok}/{len(db.FREE_TIER)} KEYS")
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

def run_app():GBTWorkstation().r.mainloop()
if __name__=="__main__":run_app()