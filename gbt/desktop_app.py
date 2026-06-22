"""
desktop_app.py - GBT Desktop Main Application
Tkinter GUI: 密钥管理 + 操盘控制 + 系统状态
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class GBTDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GBT 小土豆全能开发者 - 桌面自主操盘")
        self.root.geometry("900x620")
        self.root.configure(bg="#0d1117")
        self._build()
        self._center()
        self._refresh_status()

    def _center(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#0d1117", foreground="#c9d1d9", font=("Microsoft YaHei", 9))
        style.configure("TNotebook", background="#0d1117", borderwidth=0)
        style.configure("TNotebook.Tab", padding=[20, 8], font=("Microsoft YaHei", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#1f6feb")], foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background="#0d1117")
        style.configure("TLabel", background="#0d1117", foreground="#c9d1d9")
        style.configure("TButton", font=("Microsoft YaHei", 9), padding=6)
        style.configure("Treeview", font=("Consolas", 9), rowheight=26, background="#161b22",
                         foreground="#c9d1d9", fieldbackground="#161b22")
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 8, "bold"), background="#21262d", foreground="#c9d1d9")
        style.map("Treeview", background=[("selected", "#1f6feb")])

        # Header
        h = tk.Frame(self.root, bg="#161b22", height=48)
        h.pack(fill="x")
        tk.Label(h, text="⚕ GBT 小土豆全能开发者", bg="#161b22", fg="#58a6ff",
                 font=("Microsoft YaHei", 16, "bold")).pack(side="left", padx=16, pady=8)
        self.status_lbl = tk.Label(h, text="🟢 就绪", bg="#161b22", fg="#3fb950",
                                    font=("Consolas", 9))
        self.status_lbl.pack(side="right", padx=16, pady=8)

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self._tab_keys()
        self._tab_trade()
        self._tab_status()

        # Footer
        f = tk.Frame(self.root, bg="#161b22", height=28)
        f.pack(fill="x", side="bottom")
        tk.Label(f, text="GLM-4V + 11 providers | SQLite AES encrypted | v3.0",
                 bg="#161b22", fg="#484f58", font=("Consolas", 8)).pack(side="left", padx=10)
        tk.Label(f, text="github.com/paysssk-creator/GBTXIAOTUDOUAI",
                 bg="#161b22", fg="#484f58", font=("Consolas", 8)).pack(side="right", padx=10)


    # ── Tab 1: 密钥管理 ──
    def _tab_keys(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🗝 密钥管理")
        btn_bar = tk.Frame(tab, bg="#0d1117")
        btn_bar.pack(fill="x", padx=8, pady=(8, 2))
        ttk.Button(btn_bar, text="🔄 刷新", command=self._load_keys).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="✏ 添加密钥", command=self._import_keys).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="📋 复制", command=self._copy_key).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="🧪 测试", command=self._test_key).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="🌐 注册", command=self._reg_key).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="🗑 删除", command=self._del_key).pack(side="left", padx=2)
        cols = ("name", "ok", "key", "free")
        self.key_tree = ttk.Treeview(tab, columns=cols, show="headings", height=11)
        self.key_tree.heading("name", text="提供商"); self.key_tree.heading("ok", text="状态")
        self.key_tree.heading("key", text="密钥预览"); self.key_tree.heading("free", text="免费额度")
        self.key_tree.column("name", width=150); self.key_tree.column("ok", width=50, anchor="center")
        self.key_tree.column("key", width=340); self.key_tree.column("free", width=180)
        self.key_tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.key_tree.bind("<Double-1>", self._toggle_key)
        self._revealed = {}
        self._load_keys()

    def _load_keys(self):
        self.key_tree.delete(*self.key_tree.get_children())
        try:
            from gbt.keydb import KeyDB
            db = KeyDB()
            for pid, info in sorted(db.FREE_TIER.items(), key=lambda x: x[1]["pri"]):
                key = db.get(pid)
                p = (key[:14]+"..."+key[-6:]) if key and len(key)>20 else ("-" if not key else "***")
                self.key_tree.insert("", "end", values=(info["name"], "OK" if key else "--", p, info["free"]), tags=(pid,))
                self._revealed[pid] = key
        except Exception as e: self.status_lbl.config(text=f"Err: {e}")

    def _toggle_key(self, event):
        sel = self.key_tree.selection()
        if not sel: return
        item = self.key_tree.item(sel[0]); pid = (item.get("tags") or [None])[0]
        if not pid or not self._revealed.get(pid): return
        k = self._revealed[pid]; cur = item["values"][2]
        self.key_tree.set(sel[0], "key", k if "..." in str(cur) else (k[:14]+"..."+k[-6:] if len(k)>20 else k))

    def _copy_key(self):
        sel = self.key_tree.selection()
        if not sel: return
        pid = (self.key_tree.item(sel[0]).get("tags") or [None])[0]
        k = self._revealed.get(pid)
        if k: self.root.clipboard_clear(); self.root.clipboard_append(k); self.status_lbl.config(text=f"Copied {pid}")

    def _test_key(self):
        sel = self.key_tree.selection()
        if not sel: return
        pid = (self.key_tree.item(sel[0]).get("tags") or [None])[0]
        k = self._revealed.get(pid)
        if not k: return
        self.status_lbl.config(text=f"Testing {pid}...")
        def t():
            try:
                os.environ[(pid.upper()+"_API_KEY")] = k
                from gbt.llm import GBTLLM
                GBTLLM(provider=pid, timeout=10, max_tokens=10).invoke([{"role":"user","content":"ok"}])
                self.root.after(0, lambda: self.status_lbl.config(text=f"OK {pid}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_lbl.config(text=f"FAIL {pid}"))
        threading.Thread(target=t, daemon=True).start()

    def _reg_key(self):
        sel = self.key_tree.selection()
        if sel:
            pid = (self.key_tree.item(sel[0]).get("tags") or [None])[0]
            if pid:
                try:
                    from gbt.keydb import KeyDB
                    url = KeyDB().FREE_TIER.get(pid, {}).get("url", "")
                    if url: import webbrowser; webbrowser.open(url)
                except: pass

    def _del_key(self):
        sel = self.key_tree.selection()
        if not sel: return
        pid = (self.key_tree.item(sel[0]).get("tags") or [None])[0]
        if pid and messagebox.askyesno("Confirm", f"Delete {pid}?"):
            try:
                from gbt.keydb import KeyDB; KeyDB().remove(pid); self._load_keys()
            except: pass

    def _import_keys(self):
        try:
            from gbt.keydb import auto_import; auto_import(); self._load_keys()
            self.status_lbl.config(text="Keys imported from env")
        except Exception as e: self.status_lbl.config(text=str(e)[:60])


    # ── Tab 2: 操盘 ──
    def _tab_trade(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📈 自主操盘")
        lf = tk.Frame(tab, bg="#0d1117"); lf.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        tk.Label(lf, text="操盘指令", bg="#0d1117", fg="#58a6ff", font=("Microsoft YaHei",11,"bold")).pack(anchor="w")
        self.ti = tk.Text(lf, height=4, bg="#161b22", fg="#c9d1d9", font=("Consolas",10), insertbackground="#58a6ff", relief="flat", padx=8, pady=6)
        self.ti.pack(fill="x", pady=4); self.ti.insert("1.0","分析贵州茅台600519,如果技术指标支持则买入100股")
        bs = tk.Frame(lf, bg="#0d1117"); bs.pack(fill="x", pady=4)
        ttk.Button(bs, text="▶ 执行", command=self._run).pack(side="left", padx=2)
        ttk.Button(bs, text="⏹ 停止", command=lambda: setattr(self,'_stop',True)).pack(side="left", padx=2)
        ttk.Button(bs, text="600519", command=lambda: self._qk("分析贵州茅台600519当前走势")).pack(side="left", padx=2)
        tk.Label(lf, text="输出", bg="#0d1117", fg="#58a6ff", font=("Microsoft YaHei",11,"bold")).pack(anchor="w", pady=(8,0))
        self.to = tk.Text(lf, height=10, bg="#161b22", fg="#3fb950", font=("Consolas",9), state="disabled", relief="flat", padx=6, pady=4)
        self.to.pack(fill="both", expand=True, pady=4)
        rf = tk.Frame(tab, bg="#21262d", width=180); rf.pack(side="right", fill="y", padx=4, pady=8); rf.pack_propagate(False)
        tk.Label(rf, text="快捷操作", bg="#21262d", fg="#58a6ff", font=("Microsoft YaHei",10,"bold")).pack(pady=8)
        for t,c in [("🔍 搜索600519","搜索600519"),("📈 看K线","查看600519日K线图"),("💰 买入100股","买入600519 100股"),("💸 卖出","卖出600519全部"),("📋 持仓","查看当前持仓")]:
            ttk.Button(rf, text=t, command=lambda c=c: self._qk(c), width=14).pack(pady=3, padx=8)

    def _qk(self, task):
        self.ti.delete("1.0","end"); self.ti.insert("1.0", task); self._run()

    def _run(self):
        task = self.ti.get("1.0","end-1c").strip()
        if not task: return
        self._stop = False; self._log(f"Task: {task}")
        def do():
            try:
                from gbt.autopilot import Autopilot, compress_for_vision, ScreenState
                from gbt.llm import GBTLLM; from gbt.knowledge_base import get_system_prompt
                from PIL import ImageGrab
                llm = GBTLLM(provider="zhipu", model="glm-4v", timeout=60, max_tokens=300)
                ap = Autopilot(llm_provider=llm)
                for turn in range(1,4):
                    if self._stop: break
                    self.root.after(0, lambda t=turn: self._log(f"Turn {t}: screenshot..."))
                    img = ImageGrab.grab(); b64 = compress_for_vision(img, 480)
                    s = ScreenState(image=img, base64=b64, timestamp=time.time())

    # ── Tab 3: 系统状态 ──
    def _tab_status(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 系统状态")
        self.sys_text = tk.Text(tab, bg="#161b22", fg="#c9d1d9", font=("Consolas", 10), state="disabled", relief="flat", padx=12, pady=10)
        self.sys_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_status(self):
        self.sys_text.config(state="normal")
        self.sys_text.delete("1.0", "end")
        lines = []
        lines.append("═" * 50)
        lines.append("  GBT Desktop App v3.0 — System Status")
        lines.append("═" * 50)
        try:
            from gbt.keydb import KeyDB
            db = KeyDB()
            avail = db.available()
            lines.append(f"  API Keys: {len(avail)} available")
            for pid, name, _ in avail:
                k = db.get(pid)
                lines.append(f"    {name}: {k[:14]}... ({len(k)} chars)" if k else f"    {name}: (none)")
        except: lines.append("  Keys: load error")
        try:
            from gbt.llm import GBTLLM
            lines.append(f"  LLM: ready (zhipu + ollama + openclaw)")
        except: lines.append("  LLM: not loaded")
        try:
            from gbt.winctl import WindowsController
            w = WindowsController()
            lines.append(f"  WinCtl: {len(w.capabilities)} capabilities")
        except: pass
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            lines.append(f"  Audio: {p.get_device_count()} devices")
            p.terminate()
        except: lines.append("  Audio: pyaudio not available")
        try:
            from gbt.autopilot import Autopilot
            lines.append("  Autopilot: ready")
        except: pass
        lines.append("═" * 50)
        self.sys_text.insert("1.0", "\n".join(lines))
        self.sys_text.config(state="disabled")


def run_app():
    app = GBTDesktopApp()
    app.root.mainloop()

if __name__ == "__main__":
    run_app()

                    self.root.after(0, lambda: self._log("GLM-4V analyzing..."))
                    for a in ap.analyze(s, task):
                        if self._stop: break
                        self.root.after(0, lambda a=a: self._log(f"  [{a.action_type}] {a.reasoning[:80]}"))
                        try: ap.execute(a)
                        except: pass
                self.root.after(0, lambda: self._log("Done."))
                self.root.after(0, lambda: self.status_lbl.config(text="Ready"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"ERR: {e}"))
        self.status_lbl.config(text="Running...")
        threading.Thread(target=do, daemon=True).start()

    def _log(self, msg):
        self.to.config(state="normal"); self.to.insert("end", msg+"\n"); self.to.see("end"); self.to.config(state="disabled")
