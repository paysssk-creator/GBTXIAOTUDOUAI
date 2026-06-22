# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, json, time, os, sys, subprocess
try:
    import urllib.request as ur
except:
    import urllib2 as ur

BG="#0a0e17";C1="#111827";C2="#1f2937";BD="#2d3748"
T1="#f1f5f9";T2="#94a3b8";T3="#64748b";G="#22c55e";R="#ef4444";A="#6366f1";A2="#818cf8"

root=tk.Tk()
root.title("GBT Pro v2.1")
root.geometry("1280x800")
root.minsize(1000,650)
root.configure(bg=BG)

# ---- API helpers ----
def api_get(path, cb):
    def rn():
        try:
            rq = ur.Request("http://127.0.0.1:8765" + path)
            with ur.urlopen(rq, timeout=8) as r:
                data = json.loads(r.read())
            root.after(0, lambda: cb(data))
        except:
            root.after(0, lambda: cb(None))
    threading.Thread(target=rn, daemon=True).start()

def api_post(path, data, cb):
    def rn():
        try:
            body = json.dumps(data).encode()
            rq = ur.Request("http://127.0.0.1:8765" + path, data=body,
                           headers={"Content-Type": "application/json"})
            with ur.urlopen(rq, timeout=8) as r:
                data = json.loads(r.read())
            root.after(0, lambda: cb(data))
        except:
            root.after(0, lambda: cb(None))
    threading.Thread(target=rn, daemon=True).start()

# ---- Layout ----
main_frame = tk.Frame(root, bg=BG)
main_frame.pack(fill=tk.BOTH, expand=True)

sidebar = tk.Frame(main_frame, bg=C1, width=220)
sidebar.pack(side=tk.LEFT, fill=tk.Y)
sidebar.pack_propagate(False)

content_area = tk.Frame(main_frame, bg=BG)
content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

tk.Label(sidebar, text="GBT Pro v2.1", bg=C1, fg=A2,
         font=("Segoe UI", 14, "bold")).pack(pady=(16, 2))
tk.Label(sidebar, text="A-Stock AI Framework", bg=C1, fg=T3,
         font=("Segoe UI", 8)).pack(pady=(0, 10))

btns = {}
def add_nav(text, view):
    b = tk.Button(sidebar, text=text, bg=C1, fg=T2,
                  font=("Segoe UI", 10), bd=0, anchor="w",
                  activebackground=C2, activeforeground=T1,
                  cursor="hand2", command=lambda v=view: switch_view(v))
    b.pack(fill=tk.X, padx=8, pady=1, ipady=6)
    btns[view] = b

add_nav("  Dashboard", "dash")
add_nav("  Hacker [49]", "hacker")
add_nav("  A-Share", "trade")
add_nav("  Desktop", "desktop")

tk.Frame(sidebar, bg=C1).pack(fill=tk.BOTH, expand=True)
status_indicator = tk.Label(sidebar, text=" Online", bg=C1, fg=G,
                             font=("Segoe UI", 9))
status_indicator.pack(side=tk.BOTTOM, anchor="w", padx=12, pady=8)

# Status bar
status_bar = tk.Frame(root, bg=C2, height=26)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)
status_bar.pack_propagate(False)
status_text = tk.Label(status_bar, text="Starting Flask...", bg=C2, fg=T2,
                       font=("Segoe UI", 8))
status_text.pack(side=tk.LEFT, padx=8)
cpu_text = tk.Label(status_bar, text="", bg=C2, fg=T3, font=("Segoe UI", 8))
cpu_text.pack(side=tk.RIGHT, padx=8)

# ---- Views ----
views = {}
for name in ["dash", "hacker", "trade", "desktop"]:
    f = tk.Frame(content_area, bg=BG)
    views[name] = f

views["dash"].pack(fill=tk.BOTH, expand=True)

def switch_view(v):
    for k, w in views.items():
        if k == v:
            w.pack(fill=tk.BOTH, expand=True)
        else:
            w.pack_forget()
    for k, b in btns.items():
        b.configure(bg=C2 if k == v else C1)
    if v == "hacker":
        load_hacker()
    elif v == "trade":
        load_trade()
    elif v == "desktop":
        load_desktop()

# === DASHBOARD VIEW ===
dv = views["dash"]
row1 = tk.Frame(dv, bg=BG)
row1.pack(fill=tk.BOTH, expand=True)
row2 = tk.Frame(dv, bg=BG)
row2.pack(fill=tk.BOTH, expand=True)

def make_card(parent, title):
    f = tk.Frame(parent, bg=C1, highlightbackground=BD, highlightthickness=1)
    f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
    hdr = tk.Frame(f, bg=C1, height=28)
    hdr.pack(fill=tk.X, padx=8, pady=(4, 0))
    hdr.pack_propagate(False)
    tk.Label(hdr, text=title, bg=C1, fg=T1, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
    subt = tk.Label(hdr, text="", bg=C1, fg=T3, font=("Segoe UI", 7))
    subt.pack(side=tk.RIGHT)
    body = tk.Frame(f, bg=C1)
    body.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
    return body, subt

# LLM Card
llm_body, llm_sub = make_card(row1, "LLM Consumption")
llm_stat_frame = tk.Frame(llm_body, bg=C1)
llm_stat_frame.pack(fill=tk.X)
llm_tokens = tk.Label(llm_stat_frame, text="--", bg=C1, fg=T1, font=("Consolas", 18, "bold"))
llm_tokens.pack(side=tk.LEFT, padx=(0, 6))
tk.Label(llm_stat_frame, text="tokens", bg=C1, fg=T3, font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=(0, 14))
llm_cost = tk.Label(llm_stat_frame, text="0", bg=C1, fg=T1, font=("Consolas", 18, "bold"))
llm_cost.pack(side=tk.LEFT, padx=(0, 6))
tk.Label(llm_stat_frame, text="RMB", bg=C1, fg=T3, font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=(0, 14))
llm_model = tk.Label(llm_stat_frame, text="--", bg=C1, fg=A2, font=("Consolas", 14))
llm_model.pack(side=tk.LEFT)
llm_hist = scrolledtext.ScrolledText(llm_body, height=6, bg=C2, fg=T2,
                                      font=("Consolas", 8), bd=0, wrap=tk.WORD)
llm_hist.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

# Trade Card
trade_body, trade_sub = make_card(row1, "A-Share Account")
tr_frame = tk.Frame(trade_body, bg=C1)
tr_frame.pack(fill=tk.X)
tr_cash = tk.Label(tr_frame, text="0", bg=C1, fg=T1, font=("Consolas", 18, "bold"))
tr_cash.pack(side=tk.LEFT, padx=(0, 6))
tk.Label(tr_frame, text="cash", bg=C1, fg=T3, font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=(0, 14))
tr_pnl = tk.Label(tr_frame, text="+0", bg=C1, fg=G, font=("Consolas", 18, "bold"))
tr_pnl.pack(side=tk.LEFT, padx=(0, 6))
tk.Label(tr_frame, text="P&L", bg=C1, fg=T3, font=("Segoe UI", 7)).pack(side=tk.LEFT)
tr_wl = scrolledtext.ScrolledText(trade_body, height=6, bg=C2, fg=T2,
                                   font=("Consolas", 8), bd=0, wrap=tk.WORD)
tr_wl.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

# System Card
sys_body, sys_sub = make_card(row2, "System Resources")
sf = tk.Frame(sys_body, bg=C1)
sf.pack(fill=tk.X, pady=2)

tk.Label(sf, text="CPU", bg=C1, fg=T3, font=("Segoe UI", 8)).pack(anchor="w")
sys_cpu = tk.Label(sf, text="--%", bg=C1, fg=T1, font=("Consolas", 12, "bold"))
sys_cpu.pack(anchor="w")
sys_cpu_canvas = tk.Canvas(sf, height=8, bg=C2, bd=0, highlightthickness=0)
sys_cpu_canvas.pack(fill=tk.X, pady=(1, 6))

tk.Label(sf, text="MEM", bg=C1, fg=T3, font=("Segoe UI", 8)).pack(anchor="w")
sys_mem = tk.Label(sf, text="--%", bg=C1, fg=T1, font=("Consolas", 12, "bold"))
sys_mem.pack(anchor="w")
sys_mem_canvas = tk.Canvas(sf, height=8, bg=C2, bd=0, highlightthickness=0)
sys_mem_canvas.pack(fill=tk.X, pady=(1, 6))

tk.Label(sf, text="DISK", bg=C1, fg=T3, font=("Segoe UI", 8)).pack(anchor="w")
sys_disk = tk.Label(sf, text="--%", bg=C1, fg=T1, font=("Consolas", 12, "bold"))
sys_disk.pack(anchor="w")
sys_disk_canvas = tk.Canvas(sf, height=8, bg=C2, bd=0, highlightthickness=0)
sys_disk_canvas.pack(fill=tk.X, pady=(1, 4))

sys_procs = scrolledtext.ScrolledText(sys_body, height=9, bg=C2, fg=T2,
                                       font=("Consolas", 8), bd=0, wrap=tk.WORD)
sys_procs.pack(fill=tk.BOTH, expand=True)

# Services Card
srv_body, srv_sub = make_card(row2, "Core Services")
srv_list = scrolledtext.ScrolledText(srv_body, height=12, bg=C2, fg=T2,
                                      font=("Consolas", 8), bd=0, wrap=tk.WORD)
srv_list.pack(fill=tk.BOTH, expand=True)

# ---- DASHBOARD REFRESH ----
def refresh_dashboard():
    api_get("/api/dashboard", update_dashboard)

def update_dashboard(d):
    if not d:
        return
    # LLM
    lm = d.get("llm", {}) or {}
    tt = lm.get("totals", {}) or {}
    ct = lm.get("current", {}) or {}
    llm_tokens.config(text=str(tt.get("tokens_total", 0)))
    llm_cost.config(text=str(round(tt.get("cost_rmb", 0), 4)))
    llm_model.config(text=ct.get("model", "--") or "--")
    llm_hist.delete(1.0, tk.END)
    for h in (lm.get("history", []) or [])[-6:]:
        t = h.get("time", "")
        m = h.get("model", "")
        ti = h.get("tokens_in", 0)
        to = h.get("tokens_out", 0)
        cr = h.get("cost_rmb", 0)
        llm_hist.insert(tk.END, t + " | " + m + " | in:" + str(ti) + " out:" + str(to) + " | $" + str(round(cr,6)) + chr(10))
    # Trade
    td = d.get("trade", {}) or {}
    acct = td.get("account", {}) or {}
    tr_cash.config(text=str(acct.get("cash", 0)))
    pnl = acct.get("pnl", 0)
    tr_pnl.config(text=("+" if pnl >= 0 else "") + str(pnl), fg=G if pnl >= 0 else R)
    tr_wl.delete(1.0, tk.END)
    for w in (td.get("watchlist", []) or [])[:10]:
        tr_wl.insert(tk.END, str(w[0]) + " " + str(w[1]) + "
")
    # System
    sy = d.get("system", {}) or {}
    cpu = sy.get("cpu", 0)
    mem = sy.get("memory", 0)
    dsk = sy.get("disk", 0)
    sys_cpu.config(text=str(round(cpu, 1)) + "%")
    sys_mem.config(text=str(round(mem, 1)) + "%")
    sys_disk.config(text=str(round(dsk, 1)) + "%")
    w = sys_cpu_canvas.winfo_width() or 300
    sys_cpu_canvas.delete("all")
    sys_cpu_canvas.create_rectangle(0, 0, w * cpu / 100, 8, fill=A, outline="")
    sys_mem_canvas.delete("all")
    sys_mem_canvas.create_rectangle(0, 0, w * mem / 100, 8, fill="#a855f7", outline="")
    sys_disk_canvas.delete("all")
    sys_disk_canvas.create_rectangle(0, 0, w * dsk / 100, 8, fill="#06b6d4", outline="")
    sys_procs.delete(1.0, tk.END)
    procs = (d.get("desktop", {}).get("top_processes", []) or [])[:20]
    for p in procs:
        nm = str(p.get("name", "?"))[:30]
        pid = p.get("pid", 0)
        cp = p.get("cpu_percent", 0) or 0
        mp = p.get("memory_percent", 0) or 0
        sys_procs.insert(tk.END, nm.ljust(32) + " PID:" + str(pid).rjust(6) + " CPU:" + str(round(cp,1)).rjust(5) + " MEM:" + str(round(mp,1)).rjust(5) + "
")
    # Services
    mcp = d.get("mcp", {}) or {}
    srvs = mcp.get("servers", []) or []
    srv_sub.config(text=str(len(srvs)) + " services")
    srv_list.delete(1.0, tk.END)
    for s in srvs:
        n = s if isinstance(s, str) else (s.get("id", "") or s.get("name", ""))
        srv_list.insert(tk.END, "[ON] " + n + "
")
    # Status bar
    host = sy.get("host", "")
    status_text.config(text="Online | " + host)
    cpu_text.config(text="CPU " + str(round(cpu)) + "% | MEM " + str(round(mem)) + "% | DISK " + str(round(dsk)) + "%")

# === HACKER VIEW ===
hack_view = views["hacker"]
hack_hdr = tk.Frame(hack_view, bg=C1, height=32)
hack_hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
hack_hdr.pack_propagate(False)
tk.Label(hack_hdr, text="Hacker Capabilities", bg=C1, fg=T1,
         font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
hack_cnt = tk.Label(hack_hdr, text="", bg=C1, fg=T3, font=("Segoe UI", 8))
hack_cnt.pack(side=tk.RIGHT)

hack_canvas_frame = tk.Frame(hack_view, bg=BG)
hack_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8)
hack_canvas = tk.Canvas(hack_canvas_frame, bg=BG, bd=0, highlightthickness=0)
hack_scroll = tk.Scrollbar(hack_canvas_frame, orient=tk.VERTICAL, command=hack_canvas.yview)
hack_grid = tk.Frame(hack_canvas, bg=BG)
hack_canvas.create_window((0, 0), window=hack_grid, anchor="nw")
hack_canvas.configure(yscrollcommand=hack_scroll.set)
hack_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
hack_scroll.pack(side=tk.RIGHT, fill=tk.Y)

def on_hack_config(event):
    hack_canvas.configure(scrollregion=hack_canvas.bbox("all"))
hack_grid.bind("<Configure>", on_hack_config)

hack_log = scrolledtext.ScrolledText(hack_view, height=6, bg=C2, fg=T2,
                                      font=("Consolas", 9), bd=0, wrap=tk.WORD)
hack_log.pack(fill=tk.X, padx=8, pady=(4, 8))

def exec_cap(cid):
    hack_log.insert(1.0, "Run: " + cid + "...
")
    def cb(d):
        if d:
            ok = d.get("ok", False)
            dt = str(d.get("data", "") or d.get("error", ""))[:200]
            hack_log.insert(1.0, ("OK " if ok else "FAIL ") + cid + ": " + dt + "
")
        else:
            hack_log.insert(1.0, "ERR " + cid + "
")
    api_post("/api/hacker/exec", {"id": cid, "action": "run"}, cb)

def load_hacker():
    api_get("/api/hacker/capabilities", build_hacker)

def build_hacker(d):
    if not d:
        return
    for w in hack_grid.winfo_children():
        w.destroy()
    caps = d.get("capabilities", []) or []
    hack_cnt.config(text=str(len(caps)) + " total")
    row = None
    col = 0
    for c in caps:
        if col == 0:
            row = tk.Frame(hack_grid, bg=BG)
            row.pack(fill=tk.X, pady=1)
        color = G if c.get("mcp") else A
        cid = c.get("id", "")
        btn = tk.Button(row, text=cid[:18], bg=C2, fg=T2, font=("Segoe UI", 8),
                        bd=1, relief="solid", cursor="hand2",
                        activebackground=A, activeforeground=T1,
                        command=lambda cid=cid: exec_cap(cid))
        btn.pack(side=tk.LEFT, padx=1, pady=1)
        col += 1
        if col >= 4:
            col = 0

# === TRADE VIEW ===
trade_view = views["trade"]
tr_hdr = tk.Frame(trade_view, bg=C1, height=32)
tr_hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
tr_hdr.pack_propagate(False)
tk.Label(tr_hdr, text="A-Share Market", bg=C1, fg=T1,
         font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
tr_acct = tk.Label(tr_hdr, text="", bg=C1, fg=T3, font=("Segoe UI", 8))
tr_acct.pack(side=tk.RIGHT)
tr_quotes = scrolledtext.ScrolledText(trade_view, height=25, bg=C2, fg=T2,
                                       font=("Consolas", 10), bd=0, wrap=tk.WORD)
tr_quotes.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

def load_trade():
    api_get("/api/dashboard", lambda d: tr_acct.config(
        text="Cash: " + str((d or {}).get("trade", {}).get("account", {}).get("cash", 0)) + " | P&L: " + str(
            (d or {}).get("trade", {}).get("account", {}).get("pnl", 0))
    ) if d else None)
    api_get("/api/market", show_market)

def show_market(d):
    tr_quotes.delete(1.0, tk.END)
    if not d:
        tr_quotes.insert(tk.END, "Market data unavailable
")
        return
    if d.get("ok"):
        for idx in (d.get("indices", []) or []):
            nm = idx.get("name", "")
            pr = idx.get("price", 0)
            pct = idx.get("pct", 0)
            tr_quotes.insert(tk.END, nm.ljust(12) + str(pr).rjust(12) + ("  +" if pct >= 0 else "  ") + str(round(pct, 2)).rjust(7) + "%
")
    else:
        tr_quotes.insert(tk.END, "Error: " + str(d.get("error", "")) + "
")

# === DESKTOP VIEW ===
desk_view = views["desktop"]
dk_hdr = tk.Frame(desk_view, bg=C1, height=32)
dk_hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
dk_hdr.pack_propagate(False)
tk.Label(dk_hdr, text="Desktop Control", bg=C1, fg=T1,
         font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
dk_grid = tk.Frame(desk_view, bg=BG)
dk_grid.pack(fill=tk.X, padx=8, pady=4)
desk_log = scrolledtext.ScrolledText(desk_view, height=15, bg=C2, fg=T2,
                                      font=("Consolas", 9), bd=0, wrap=tk.WORD)
desk_log.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

desk_actions = [
    ("Screenshot", "screenshot"),
    ("Browser", "browser_open"),
    ("Maximize", "window_maximize"),
    ("Keyboard", "keyboard_type"),
    ("Hotkey", "keyboard_hotkey"),
    ("Mouse", "mouse_click"),
    ("Processes", "process_list"),
    ("Kill Proc", "process_kill"),
    ("Focus Win", "window_focus"),
    ("Volume", "volume_control"),
    ("Lock", "system_lock"),
]

def desk_action(cid):
    desk_log.insert(1.0, "Run: " + cid + "...
")
    def cb(d):
        if d and d.get("ok"):
            desk_log.insert(1.0, "OK " + cid + "
")
        else:
            desk_log.insert(1.0, "FAIL " + cid + "
")
    api_post("/api/hacker/exec", {"id": cid, "action": "run"}, cb)

def load_desktop():
    for w in dk_grid.winfo_children():
        w.destroy()
    for name, cid in desk_actions:
        btn = tk.Button(dk_grid, text=name, bg=C2, fg=T2, font=("Segoe UI", 9),
                        bd=1, relief="solid", cursor="hand2",
                        activebackground=A, activeforeground=T1,
                        command=lambda cid=cid: desk_action(cid))
        btn.pack(side=tk.LEFT, padx=2, pady=3)
    api_get("/api/system", lambda d: desk_log.insert(1.0,
        "System: CPU " + str((d or {}).get("cpu", 0)) + "% MEM " + str(
            (d or {}).get("memory", 0)) + "%
") if d else None)

# === FLASK STARTER + MAIN LOOP ===
flask_proc = None

def start_flask():
    global flask_proc
    dir_path = os.path.dirname(os.path.abspath(__file__))
    flask_proc = subprocess.Popen(["python", "desktop_app.py"],
                                   cwd=dir_path,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    status_text.config(text="Starting Flask...")
    time.sleep(5)
    status_text.config(text="Online")
    refresh_dashboard()

threading.Thread(target=start_flask, daemon=True).start()

# Start refresh loop after 3s
root.after(3000, refresh_dashboard)

def refresh_loop():
    refresh_dashboard()
    root.after(5000, refresh_loop)

root.after(8000, refresh_loop)
root.mainloop()
