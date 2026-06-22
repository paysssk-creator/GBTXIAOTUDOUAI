"""
key_window.py - GBT 密钥管理窗口
Tkinter GUI: 查看/添加/复制/测试API密钥
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, threading, webbrowser, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class KeyManagerWindow:
    def __init__(self, master=None):
        self.master = master or tk.Tk()
        self.master.title("GBT 密钥管理器 - 天帝宝库")
        self.master.geometry("750x520")
        self.master.resizable(True, True)
        self.master.configure(bg="#1a1a2e")
        self._revealed = {}
        self._build_ui()
        self.load_keys()
        self.master.update_idletasks()
        w, h = self.master.winfo_width(), self.master.winfo_height()
        sw, sh = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        self.master.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1a1a2e", foreground="#e0e0e0", font=("Microsoft YaHei", 10))
        style.configure("TButton", font=("Microsoft YaHei", 9), padding=4)
        style.configure("Treeview", font=("Consolas", 10), rowheight=28, background="#16213e", foreground="#e0e0e0", fieldbackground="#16213e")
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 9, "bold"), background="#0f3460", foreground="#ffffff")
        style.map("Treeview", background=[("selected", "#e94560")])

        header = tk.Frame(self.master, bg="#0f3460", height=50)
        header.pack(fill="x")
        tk.Label(header, text="🗝 天帝宝库 - API密钥管理器", bg="#0f3460", fg="#ffffff",
                 font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=15, pady=10)
        tk.Label(header, text="v2.0", bg="#0f3460", fg="#a0a0c0",
                 font=("Consolas", 9)).pack(side="right", padx=15, pady=10)

        table_frame = tk.Frame(self.master, bg="#1a1a2e")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("provider", "status", "key_preview", "free_tier")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        self.tree.heading("provider", text="提供商", anchor="w")
        self.tree.heading("status", text="状态", anchor="center")
        self.tree.heading("key_preview", text="密钥预览", anchor="w")
        self.tree.heading("free_tier", text="免费额度", anchor="w")
        self.tree.column("provider", width=140, minwidth=100)
        self.tree.column("status", width=60, anchor="center")
        self.tree.column("key_preview", width=350, minwidth=200)
        self.tree.column("free_tier", width=180, minwidth=120)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_double_click)

        btn_frame = tk.Frame(self.master, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="🔄 刷新", command=self.load_keys).pack(side="left", padx=3)

    def load_keys(self):
        self.tree.delete(*self.tree.get_children())
        try:
            from gbt.keydb import KeyDB
            db = KeyDB()
            for pid, info in sorted(db.FREE_TIER.items(), key=lambda x: x[1]["pri"]):
                key = db.get(pid)
                preview = key[:12] + "..." + key[-6:] if key and len(key) > 20 else ("(not set)" if not key else "***")
                status = "OK" if key else "--"
                self.tree.insert("", "end", values=(info["name"], status, preview, info["free"]), tags=(pid,))
                self._revealed[pid] = key
            self.status_var.set(f"Ready - {len(db.available())} keys")
        except Exception as e:
            self.status_var.set(f"Load error: {e}")

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        tags = item.get("tags", [])
        if not tags: return
        pid = tags[0]
        key = self._revealed.get(pid)
        if not key: return
        cur = item["values"][2]
        if "..." in str(cur):
            self.tree.set(sel[0], "key_preview", key)
            self.status_var.set(f"Revealed: {pid}")
        else:
            p = key[:12] + "..." + key[-6:] if len(key) > 20 else "***"
            self.tree.set(sel[0], "key_preview", p)
            self.status_var.set(f"Hidden: {pid}")

    def _copy_selected(self):
        sel = self.tree.selection()
        if not sel: return
        pid = (self.tree.item(sel[0]).get("tags") or [None])[0]
        if not pid: return
        key = self._revealed.get(pid)
        if key:
            self.master.clipboard_clear(); self.master.clipboard_append(key)
            self.status_var.set(f"Copied: {pid}")
        else: self.status_var.set("No key")

    def _test_selected(self):
        sel = self.tree.selection()
        if not sel: return
        pid = (self.tree.item(sel[0]).get("tags") or [None])[0]
        if not pid: return
        key = self._revealed.get(pid)
        if not key: return
        self.status_var.set(f"Testing: {pid}...")
        threading.Thread(target=lambda: self._run_test(pid, key), daemon=True).start()

    def _run_test(self, pid, key):
        try:
            os.environ[(pid.upper()+"_API_KEY")] = key
            from gbt.llm import GBTLLM
            GBTLLM(provider=pid, timeout=10, max_tokens=10).invoke([{"role":"user","content":"ok"}])
            self.master.after(0, lambda: self.status_var.set(f"OK: {pid}"))
        except Exception as e:
            self.master.after(0, lambda: self.status_var.set(f"FAIL {pid}: {str(e)[:80]}"))

    def _open_register(self):
        sel = self.tree.selection()
        if not sel: return
        pid = (self.tree.item(sel[0]).get("tags") or [None])[0]
        if pid:
            try:
                from gbt.keydb import KeyDB
                url = KeyDB().FREE_TIER.get(pid, {}).get("url", "")
                if url: webbrowser.open(url)
            except: pass

        ttk.Button(btn_frame, text="✏ 添加密钥", command=self._add_key_dialog).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="📋 复制选中", command=self._copy_selected).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🧪 测试连接", command=self._test_selected).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🌐 注册页面", command=self._open_register).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🗑 删除", command=self._delete_selected).pack(side="left", padx=3)

        self.status_var = tk.StringVar(value="就绪 - 双击查看完整密钥")
        tk.Label(self.master, textvariable=self.status_var, bg="#0f3460", fg="#a0a0c0",
                 font=("Microsoft YaHei", 9), anchor="w", padx=10).pack(fill="x", side="bottom")


    def _add_key_dialog(self):
        d = tk.Toplevel(self.master)
        d.title("Add Key"); d.geometry("400x220"); d.configure(bg="#1a1a2e")
        d.transient(self.master); d.grab_set()
        tk.Label(d, text="Provider:", bg="#1a1a2e", fg="#eee", font=("Arial",10)).pack(anchor="w", padx=15, pady=(15,2))
        pv = tk.StringVar()
        try:
            from gbt.keydb import KeyDB
            opts = [f"{p} - {i['name']}" for p,i in KeyDB().FREE_TIER.items()]
        except: opts = ["zhipu - GLM"]
        ttk.Combobox(d, textvariable=pv, values=opts, width=28, font=("Consolas",10)).pack(padx=15,pady=3)
        if opts: pv.set(opts[0])
        tk.Label(d, text="API Key:", bg="#1a1a2e", fg="#eee", font=("Arial",10)).pack(anchor="w", padx=15, pady=(10,2))
        ke = tk.Entry(d, font=("Consolas",10), width=40); ke.pack(padx=15,pady=3)
        def do():
            sel = pv.get().split(" - ")[0] if pv.get() else ""
            k = ke.get().strip()
            if sel and k:
                try:
                    from gbt.keydb import KeyDB
                    KeyDB().save(sel, k, free=True, note="manual")
                    d.destroy(); self.load_keys()
                except Exception as e: messagebox.showerror("Error", str(e))
        tf = tk.Frame(d, bg="#1a1a2e"); tf.pack(pady=15)
        ttk.Button(tf, text="Save", command=do).pack(side="left", padx=5)
        ttk.Button(tf, text="Cancel", command=d.destroy).pack(side="left", padx=5)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        pid = (self.tree.item(sel[0]).get("tags") or [None])[0]
        if pid and messagebox.askyesno("Confirm", f"Delete {pid}?"):
            try:
                from gbt.keydb import KeyDB
                KeyDB().remove(pid)
                self.load_keys()
            except Exception as e: self.status_var.set(str(e))


def show_key_window(master=None):
    win = KeyManagerWindow(master)
    if master is None: win.master.mainloop()
    return win

if __name__ == "__main__":
    show_key_window()
