"""
app.py — GBT桌面智能体APP
双模式: tkinter GUI / Flask Web
"""

import os, sys, threading, time
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
    GUI_OK = True
except: GUI_OK = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.gbt_agent import GBTAgent
from tools.mcp_tools import register_all_mcp_tools
from gbt.mcp import get_mcp, call_mcp


class GBTDesktopApp:

    def __init__(self, provider="auto", project=None):
        self.p = project or os.getcwd(); self.provider = provider
        self.agent = None; self.r = None; self.st = None
        self.cd = None; self.ci = None; self.qe = None
        self._init_agent()
        if GUI_OK: self._gui()
        else: self._web()

    def _init_agent(self):
        try:
            self.agent = GBTAgent(provider=self.provider, project_root=self.p)
            register_all_mcp_tools(self.agent._tools, self.p)
        except Exception as e:
            print(f"⚠️ Agent: {e}")
            try: self.agent = GBTAgent(provider="ollama", project_root=self.p)
            except: print("❌ 无LLM可用")

    # ── GUI ──
    def _gui(self):
        self.r = tk.Tk(); self.r.title("⚕ GBT小土豆 — 桌面智能体")
        self.r.geometry("950x680"); self.r.minsize(550,380)
        bg, fg = "#1e1e2e", "#cdd6f4"; self.r.configure(bg=bg)
        self._bar(bg,fg)
        pw = ttk.PanedWindow(self.r, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        L = ttk.Frame(pw, width=230); self._sidepanel(L,bg,fg); pw.add(L,weight=0)
        R = ttk.Frame(pw); self._chatpanel(R,bg,fg); pw.add(R,weight=1)
        self._statusbar(bg,fg)
        self.r.protocol("WM_DELETE_WINDOW", lambda: self.r.destroy())
        self.r.mainloop()

    def _bar(self,bg,fg):
        b = tk.Frame(self.r, bg="#181825", height=36)
        b.pack(fill=tk.X)
        tk.Label(b, text="⚕ GBT v1.4", bg="#181825", fg="#f5c2e7",
                font=("Microsoft YaHei",12,"bold")).pack(side=tk.LEFT, padx=10)
        self.st = tk.Label(b, text="🟢", bg="#181825", fg="#a6e3a1")
        self.st.pack(side=tk.RIGHT, padx=10)

    def _sidepanel(self,p,bg,fg):
        tk.Label(p,text="🔧 工具箱",bg=bg,fg=fg,font=("Microsoft YaHei",11,"bold")).pack(pady=5)
        btns = [
            ("🧠 推理",lambda:self._dlg("深度推理","问题:")),
            ("🔍 扫描",lambda:self._mcp("scanner")),
            ("📋 审计",lambda:self._mcp("audit","--strict")),
            ("🧬 进化",lambda:self._evolve()),
            ("🪞 镜像",lambda:self._mcp("mirror-deploy")),
            ("🔧 修复",lambda:self._mcp("auto-fix","--confirm")),
            ("💾 备份",lambda:self._backup()),
            ("🖥️ 系统",lambda:self._sys()),
            ("🔌 MCP",lambda:self._show_mcp()),
        ]
        for t, c in btns:
            tk.Button(p, text=t, command=c, bg="#313244", fg=fg,
                relief=tk.FLAT, cursor="hand2", font=("Microsoft YaHei",10)
            ).pack(fill=tk.X, pady=2, padx=5)
        tk.Label(p,text="快捷推理:",bg=bg,fg=fg).pack(pady=(10,0))
        self.qe = tk.Entry(p, bg="#313244", fg=fg, insertbackground=fg)
        self.qe.pack(fill=tk.X, padx=5)
        self.qe.bind("<Return>", lambda e: self._qask())
        tk.Button(p, text="⚡推理", command=self._qask,
                 bg="#cba6f7", fg="#1e1e2e").pack(fill=tk.X, padx=5, pady=2)

    def _chatpanel(self,p,bg,fg):
        tk.Label(p,text="💬 对话",bg=bg,fg=fg,font=("Microsoft YaHei",11,"bold")).pack(pady=3)
        self.cd = scrolledtext.ScrolledText(p, bg="#313244", fg=fg,
            font=("Consolas",10), wrap=tk.WORD, state=tk.DISABLED)
        self.cd.pack(fill=tk.BOTH, expand=True, padx=3)
        inf = tk.Frame(p, bg=bg); inf.pack(fill=tk.X, padx=3, pady=3)
        self.ci = tk.Text(inf, height=3, bg="#313244", fg=fg, font=("Consolas",10))
        self.ci.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ci.bind("<Control-Return>", lambda e: self._send())
        tk.Button(inf, text="→", command=self._send,
                 bg="#89b4fa", fg="#1e1e2e", width=6).pack(side=tk.RIGHT)

    def _statusbar(self,bg,fg):
        m = get_mcp(); s = len(m.list_servers())
        llm = f"{self.agent.llm.provider_name}" if self.agent and hasattr(self.agent,'llm') else "?"
        self.sb = tk.Label(self.r, text=f"MCP:{s} | LLM:{llm} | {self.p}",
                          bg="#181825", fg="#6c7086", anchor=tk.W)
        self.sb.pack(fill=tk.X, side=tk.BOTTOM)

    def _add(self, role, txt):
        self.cd.config(state=tk.NORMAL)
        ic = {"assistant":"🤖","user":"👤","reasoner":"🧠","mcp":"🔌","evolve":"🧬","system":"📌"}
        self.cd.insert(tk.END, f"\n{ic.get(role,'•')} ", "r")
        self.cd.insert(tk.END, txt[:3000]+"\n"); self.cd.see(tk.END)
        self.cd.config(state=tk.DISABLED)

    def _send(self):
        t = self.ci.get("1.0", tk.END).strip()
        if not t or not self.agent: return
        self.ci.delete("1.0", tk.END); self._add("user", t)
        threading.Thread(target=self._chat_do, args=(t,), daemon=True).start()

    def _chat_do(self, t):
        self.st.config(text="🟡"); self.r.update()
        try:
            r = self.agent.run(t)
            self.r.after(0, lambda: self._add("assistant", r[:3000]))
        except Exception as e:
            self.r.after(0, lambda: self._add("system", f"❌{e}"))
        self.r.after(0, lambda: self.st.config(text="🟢"))

    def _qask(self):
        t = self.qe.get().strip()
        if not t: return
        self.qe.delete(0, tk.END); self._add("user", f"[推理] {t}")
        threading.Thread(target=self._reason_do, args=(t,"chain"), daemon=True).start()

    def _reason_do(self, q, m):
        self.st.config(text="🧠")
        try:
            r = self.agent.deep_reason(q, m)
            self.r.after(0, lambda: self._add("reasoner",
                f"## {r.mode.value} 置信度{r.confidence:.0%}\n{r.conclusion[:2000]}"))
        except Exception as e:
            self.r.after(0, lambda: self._add("system", f"❌{e}"))
        self.r.after(0, lambda: self.st.config(text="🟢"))

    def _dlg(self, title, prompt):
        d = tk.Toplevel(self.r); d.title(title); d.geometry("450x110")
        d.configure(bg="#1e1e2e")
        tk.Label(d, text=prompt, bg="#1e1e2e", fg="#cdd6f4").pack(pady=5)
        e = tk.Entry(d, bg="#313244", fg="#cdd6f4", width=55); e.pack(pady=5)
        def ok():
            t = e.get().strip()
            if t: d.destroy(); threading.Thread(target=lambda: self._reason_do(t,"chain"), daemon=True).start()
        e.bind("<Return>", lambda ev: ok())
        tk.Button(d, text="确认", command=ok, bg="#89b4fa").pack()

    def _mcp(self, s, a=""):
        threading.Thread(target=lambda: self._mcp_do(s,a), daemon=True).start()

    def _mcp_do(self, s, a):
        self.st.config(text="🔌")
        r = call_mcp(s, "", a)
        ic = "✅" if r.ok else "❌"
        self.r.after(0, lambda: self._add("mcp", f"{ic} {s}: {r.data[:1200] if r.data else r.error}"))
        self.r.after(0, lambda: self.st.config(text="🟢"))

    def _evolve(self):
        threading.Thread(target=self._evolve_do, daemon=True).start()

    def _evolve_do(self):
        self.st.config(text="🧬")
        try:
            r = self.agent.evolve("桌面")
            self.r.after(0, lambda: self._add("evolve", f"{'✅' if r.success else '❌'} {r.summary}"))
        except Exception as e:
            self.r.after(0, lambda: self._add("system", f"❌{e}"))
        self.r.after(0, lambda: self.st.config(text="🟢"))

    def _backup(self):
        import subprocess
        try:
            r = subprocess.run("git add -A && git commit -m 'desktop'",
                shell=True, capture_output=True, text=True, cwd=self.p, timeout=10)
            self._add("system", f"💾 {r.stdout[:300] or r.stderr[:300]}")
        except: self._add("system", "💾 Git不可用")

    def _sys(self):
        import platform
        try:
            import psutil
            i = (f"🖥️ {platform.system()} {platform.release()} | "
                 f"CPU:{psutil.cpu_count()}核{psutil.cpu_percent()}% | "
                 f"RAM:{psutil.virtual_memory().percent}%")
        except:
            i = f"🖥️ {platform.system()} {platform.release()}"
        self._add("system", i)

    def _show_mcp(self):
        s = get_mcp().list_servers()
        self._add("system", f"## 🔌 MCP({len(s)})\n" + "\n".join(f"- {n}" for n in s))

    def _web(self):
        try:
            from flask import Flask, request, jsonify
            a = Flask(__name__)
            @a.route("/api/chat", methods=["POST"])
            def c():
                d = request.json
                r = self.agent.run(d.get("text",""))[:5000] if self.agent else "未初始化"
                return jsonify({"response": r})
            @a.route("/api/reason", methods=["POST"])
            def r():
                d = request.json
                r = self.agent.deep_reason(d.get("text",""), d.get("mode","chain"))
                return jsonify({"mode": r.mode.value, "conclusion": r.conclusion, "confidence": r.confidence})
            @a.route("/api/mcp")
            def m(): return jsonify({"servers": get_mcp().list_servers()})
            @a.route("/api/mcp/<s>", methods=["POST"])
            def mc(s):
                r = call_mcp(s)
                return jsonify({"ok": r.ok, "data": r.data[:3000], "error": r.error})
            print("\n🌐 http://localhost:8765\n")
            a.run(host="127.0.0.1", port=8765, debug=False)
        except ImportError:
            print("❌ pip install flask")


def main():
    import argparse
    p = argparse.ArgumentParser(description="GBT桌面智能体")
    p.add_argument("--provider", default="auto"); p.add_argument("--project", default=os.getcwd())
    p.add_argument("--web", action="store_true")
    a = p.parse_args()
    if a.web: global GUI_OK; GUI_OK = False
    GBTDesktopApp(provider=a.provider, project=a.project)

if __name__ == "__main__":
    main()

