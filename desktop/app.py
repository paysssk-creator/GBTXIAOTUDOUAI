"""
app.py — GBT桌面智能体APP v2.0
双模式: tkinter GUI 主页 / Flask Web 主页
精心设计的现代化桌面AI智能体界面
"""

import os, sys, threading, time, json, platform
from typing import Optional
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    GUI_OK = True
except:
    GUI_OK = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.gbt_agent import GBTAgent
from tools.mcp_tools import register_all_mcp_tools
from gbt.mcp import get_mcp, call_mcp
from gbt.providers import PROVIDERS, AutoKeyConfig


# ═══════════════════════════════════════════
#  GBT Desktop App v2.0 - Homepage Design
# ═══════════════════════════════════════════

class GBTDesktopApp:

    def __init__(self, provider="auto", project=None, web_mode=False):
        self.p = project or os.getcwd()
        self.provider = provider
        self.agent = None
        self._init_agent()
        if web_mode:
            self._launch_web()
        elif GUI_OK:
            self._launch_gui()
        else:
            self._launch_web()

    def _init_agent(self):
        try:
            self.agent = GBTAgent(provider=self.provider, project_root=self.p)
            register_all_mcp_tools(self.agent._tools, self.p)
            print(f"GBT Agent [{self.agent.llm.provider_name}] OK")
        except Exception as e:
            print(f"Agent init: {e}")
            try:
                self.agent = GBTAgent(provider="ollama", project_root=self.p)
                register_all_mcp_tools(self.agent._tools, self.p)
            except:
                print("No LLM available - demo mode")
                self.agent = None

    # ═══════════════════════ TKINTER GUI ═══════════════════════

    def _launch_gui(self):
        self.r = tk.Tk()
        self.r.title("GBT - AI Desktop Agent v2.0")
        self.r.geometry("1100x720")
        self.r.minsize(900, 600)
        C = {
            "base":"#1e1e2e","mantle":"#181825","crust":"#11111b",
            "surface0":"#313244","surface1":"#45475a","text":"#cdd6f4",
            "subtext":"#a6adc8","subtext0":"#6c7086","blue":"#89b4fa",
            "lavender":"#b4befe","mauve":"#cba6f7","pink":"#f5c2e7",
            "red":"#f38ba8","peach":"#fab387","yellow":"#f9e2af",
            "green":"#a6e3a1","teal":"#94e2d5","sky":"#89dceb",
        }
        self.C = C
        self.r.configure(bg=C["base"])
        self._build_titlebar()
        self._build_homepage()
        self._build_statusbar()
        self.r.protocol("WM_DELETE_WINDOW", self._on_close)
        self.r.mainloop()

    def _build_chatarea(self, p):
        C = self.C
        wf = tk.Frame(p, bg=C["base"]); wf.pack(fill=tk.X, pady=(8,4))
        tk.Label(wf, text="Chat", bg=C["base"], fg=C["text"],
                font=("Microsoft YaHei",11,"bold")).pack(side=tk.LEFT)
        tk.Button(wf, text="Clear", command=self._clear_chat, bg=C["surface0"],
                fg=C["subtext"], relief=tk.FLAT, cursor="hand2",
                font=("Microsoft YaHei",8), bd=0, padx=8).pack(side=tk.RIGHT)
        self.cd = scrolledtext.ScrolledText(p, bg=C["surface0"], fg=C["text"],
                font=("Consolas",10), wrap=tk.WORD, state=tk.DISABLED, relief=tk.FLAT)
        self.cd.pack(fill=tk.BOTH, expand=True, padx=2)
        for role, c, f in [("assistant",C["green"],("Consolas",10)),
                           ("user",C["blue"],("Consolas",10,"bold")),
                           ("system",C["subtext0"],("Consolas",9)),
                           ("mcp",C["mauve"],("Consolas",9)),
                           ("reasoner",C["peach"],("Consolas",10,"bold")),
                           ("evolve",C["teal"],("Consolas",10)),
                           ("welcome",C["pink"],("Microsoft YaHei",11,"bold"))]:
            self.cd.tag_config(role, foreground=c, font=f)
        self._add_chat("welcome", self._welcome())
        inf = tk.Frame(p, bg=C["base"]); inf.pack(fill=tk.X, padx=2, pady=(4,2))
        self.ci = tk.Text(inf, height=3, bg=C["surface1"], fg=C["text"],
                font=("Consolas",10), relief=tk.FLAT, padx=8, pady=6)
        self.ci.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ci.bind("<Control-Return>", lambda e: self._send())
        tk.Button(inf, text="Send", command=self._send, bg=C["blue"],
                fg=C["crust"], relief=tk.FLAT, cursor="hand2",
                font=("Microsoft YaHei",10,"bold"), bd=0, width=8).pack(side=tk.RIGHT, padx=(4,0),fill=tk.Y)

    def _build_dashboard(self, p):
        C = self.C
        tk.Label(p, text="Dashboard", bg=C["base"], fg=C["text"],
                font=("Microsoft YaHei",11,"bold")).pack(pady=(10,8), anchor=tk.W)
        self._card(p, "System", self._sys_info())
        mcp = get_mcp(); srvs = mcp.list_servers()
        self._card(p, "MCP Servers", f"Connected: {len(srvs)}\n"+"\n".join(f"  {s}" for s in srvs[:8]))
        disc = AutoKeyConfig.scan(); av = sum(1 for v in disc.values() if v["status"]=="available")
        self._card(p, "API Keys", f"Available: {av}/{len(PROVIDERS)}\n"+"\n".join(
            f"  {'OK' if v['status']=='available' else '--'} {cfg['name']}" for pid,info in list(disc.items())[:13]))
        tk.Label(p, text="Quick Commands", bg=C["base"],
                fg=C["subtext0"], font=("Microsoft YaHei",9)).pack(pady=(10,2),anchor=tk.W,padx=6)
        for ct, cf in [("tools",lambda:self._send_cmd("tools")),
                       ("keys",lambda:self._send_cmd("keys")),
                       ("status",lambda:self._send_cmd("status")),
                       ("help",lambda:self._send_cmd("help"))]:
            tk.Button(p, text=f"  {ct}", command=cf, bg=C["surface0"],
                fg=C["text"], relief=tk.FLAT, cursor="hand2",
                font=("Consolas",9), bd=0, padx=10, pady=3, anchor=tk.W
                ).pack(fill=tk.X, pady=1, padx=6)
        tk.Label(p, text="GBT v2.0", bg=C["base"],
                fg=C["subtext0"], font=("Consolas",8)).pack(side=tk.BOTTOM, pady=(0,8))

    def _reason_dlg(self):
        d = tk.Toplevel(self.r); d.title("Deep Reason"); d.geometry("500x180")
        d.configure(bg=self.C["base"])
        tk.Label(d, text="Question:", bg=self.C["base"], fg=self.C["text"],
                font=("Microsoft YaHei",11)).pack(pady=(10,5))
        e = tk.Entry(d, bg=self.C["surface0"], fg=self.C["text"],
                    font=("Consolas",10), relief=tk.FLAT)
        e.pack(fill=tk.X, padx=15, pady=5, ipady=4)
        mf = tk.Frame(d, bg=self.C["base"]); mf.pack(pady=5)
        mv = tk.StringVar(value="chain")
        for t,v in [("Chain","chain"),("Tree","tree"),("SWOT","swot"),
                    ("Root","root_cause"),("Decide","decision"),("Estimate","estimate"),
                    ("Compare","compare"),("Plan","plan")]:
            tk.Radiobutton(mf, text=t, variable=mv, value=v, bg=self.C["base"],
                fg=self.C["text"], selectcolor=self.C["surface0"],
                font=("Microsoft YaHei",8)).pack(side=tk.LEFT, padx=2)
        def go():
            q = e.get().strip()
            if not q: return
            m = mv.get(); d.destroy()
            self._add_chat("user", f"[Reason:{m}] {q}")
            threading.Thread(target=self._do_reason, args=(q,m), daemon=True).start()
        e.bind("<Return>", lambda ev: go())
        tk.Button(d, text="Start", command=go, bg=self.C["blue"],
                fg=self.C["crust"], font=("Microsoft YaHei",10,"bold"),
                relief=tk.FLAT, bd=0, padx=20, pady=4).pack(pady=5)

    def _multi_dlg(self):
        d = tk.Toplevel(self.r); d.title("Multi-Reason"); d.geometry("400x120")
        d.configure(bg=self.C["base"])
        tk.Label(d, text="Multi-mode (chain+swot+root):", bg=self.C["base"],
                fg=self.C["text"], font=("Microsoft YaHei",10)).pack(pady=(10,5))
        e = tk.Entry(d, bg=self.C["surface0"], fg=self.C["text"],
                    font=("Consolas",10), relief=tk.FLAT)
        e.pack(fill=tk.X, padx=15, pady=5, ipady=4)
        def go():
            q = e.get().strip()
            if not q: return
            d.destroy()
            self._add_chat("user", f"[Multi] {q}")
            threading.Thread(target=self._do_multi, args=(q,), daemon=True).start()
        e.bind("<Return>", lambda ev: go())
        tk.Button(d, text="Start", command=go, bg=self.C["mauve"],
                fg=self.C["crust"], relief=tk.FLAT, bd=0, padx=20, pady=4).pack(pady=5)


    def _do_reason(self, q, m):
        self._up("reason")
        try:
            r = self.agent.deep_reason(q, m)
            out = f"## {m} Conf:{r.confidence:.0%}\n{r.conclusion[:2000]}\n{r.duration:.1f}s"
            self.r.after(0, lambda: self._add_chat("reasoner", out))
        except Exception as e:
            self.r.after(0, lambda: self._add_chat("system", f"ERR: {e}"))
        self._up("ok")

    def _do_multi(self, q):
        self._up("reason")
        try:
            rs = self.agent.reason_multi(q, ["chain","swot","root_cause"])
            for r in rs:
                out = f"## {r.mode.value} Conf:{r.confidence:.0%}\n{r.conclusion[:1000]}\n---"
                self.r.after(0, lambda o=out: self._add_chat("reasoner", o))
        except Exception as e:
            self.r.after(0, lambda: self._add_chat("system", f"ERR: {e}"))
        self._up("ok")

    def _mcp_async(self, srv, a=""):
        self._add_chat("system", f"MCP/{srv}...")
        threading.Thread(target=self._do_mcp, args=(srv,a), daemon=True).start()

    def _do_mcp(self, srv, a):
        self._up("mcp")
        r = call_mcp(srv, "", a)
        ic = "OK" if r.ok else "FAIL"
        d = r.data[:1500] if r.data else r.error
        self.r.after(0, lambda: self._add_chat("mcp", f"{ic} {srv}: {d}"))
        self._up("ok")

    def _evolve_async(self):
        self._add_chat("system", "6-Step Evolve starting...")
        threading.Thread(target=self._do_evolve, daemon=True).start()

    def _do_evolve(self):
        self._up("evolve")

    # ═══════════════════════ FLASK WEB MODE ═══════════════════════

    def _launch_web(self):
        try:
            from flask import Flask, request, jsonify, render_template_string
            app = Flask(__name__)

            @app.route("/")
            def home():
                return render_template_string(WEB_HTML)

            @app.route("/api/chat", methods=["POST"])
            def api_chat():
                d = request.json or {}
                if not self.agent: return jsonify({"error":"Agent not initialized"})
                r = self.agent.run(d.get("text",""))[:5000]
                return jsonify({"response":r})

            @app.route("/api/reason", methods=["POST"])
            def api_reason():
                d = request.json or {}
                if not self.agent: return jsonify({"error":"Agent not initialized"})
                r = self.agent.deep_reason(d.get("text",""), d.get("mode","chain"))
                return jsonify({"mode":r.mode.value,"conclusion":r.conclusion,
                               "confidence":r.confidence,"plan":r.plan})

            @app.route("/api/status")
            def api_status():
                mcp = get_mcp(); disc = AutoKeyConfig.scan()
                return jsonify({
                    "mcp_servers": mcp.list_servers(),
                    "mcp_count": len(mcp.list_servers()),
                    "llm": self.agent.llm.provider_name if self.agent else "N/A",
                    "model": self.agent.llm.model if self.agent else "N/A",
                    "keys_available": sum(1 for v in disc.values() if v["status"]=="available"),
                    "keys_total": len(PROVIDERS),
                    "platform": platform.system(),
                    "python": platform.python_version(),
                })

            @app.route("/api/mcp")
            def api_mcp_list():
                return jsonify({"servers": get_mcp().list_servers()})

            @app.route("/api/mcp/<server>", methods=["POST"])
            def api_mcp(server):
                r = call_mcp(server);
                return jsonify({"ok":r.ok,"data":r.data[:3000],"error":r.error})

            @app.route("/api/providers")
            def api_providers():

    # Web homepage HTML loaded from template file
    WEB_HTML = ""
    _template_path = os.path.join(os.path.dirname(__file__), "templates", "homepage.html")
    if os.path.exists(_template_path):
        with open(_template_path, "r", encoding="utf-8") as f:
            WEB_HTML = f.read()


def main():
    import argparse
    p = argparse.ArgumentParser(description="GBT Desktop Agent v2.0")
    p.add_argument("--provider", default="auto")
    p.add_argument("--project", default=os.getcwd())
    p.add_argument("--web", action="store_true")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    web_mode = args.web or not GUI_OK
    GBTDesktopApp(provider=args.provider, project=args.project, web_mode=web_mode)


if __name__ == "__main__":
    main()
                disc = AutoKeyConfig.scan()
                r = {}
                for pid, info in disc.items():
                    cfg = info["config"]
                    r[pid] = {"name":cfg["name"],"status":info["status"],
                              "models":cfg.get("models",[]),"pricing":cfg.get("pricing","")}
                return jsonify(r)

            print("\n" + "="*50)
            print("  GBT v2.0 Web Homepage")
            print("  http://localhost:8765")
            print("="*50 + "\n")
            app.run(host="127.0.0.1", port=8765, debug=False)
        except ImportError:
            print("ERROR: pip install flask")
        try:
            rpt = self.agent.evolve("desktop-trigger")
            ic = "OK" if rpt.success else "FAIL"
            ss = ", ".join(f"{s.name}={s.status.value}" for s in rpt.steps)
            self.r.after(0, lambda: self._add_chat("evolve", f"{ic} Steps: {ss}"))
        except Exception as e:
            self.r.after(0, lambda: self._add_chat("system", f"ERR: {e}"))
        self._up("ok")

    def _winctl_a(self, f, a):
        threading.Thread(target=self._do_winctl, args=(f,a), daemon=True).start()

    def _do_winctl(self, f, a):
        self._up("sys")
        try:
            r = self.agent.winctl(f, a)
            d = (r.data or r.error)[:1500]
            self.r.after(0, lambda: self._add_chat("system", f"WinCtl {f}.{a}: {d}"))
        except Exception as e:
            self.r.after(0, lambda: self._add_chat("system", f"ERR: {e}"))
        self._up("ok")

    def _git_backup(self):
        import subprocess
        try:
            r = subprocess.run("git add -A && git commit -m desktop",
                shell=True, capture_output=True, text=True, cwd=self.p, timeout=10)
            self._add_chat("system", f"Git: {r.stdout[:200] or 'Done'}")
        except: self._add_chat("system", "Git unavailable")

    def _clear_chat(self):
        self.cd.config(state=tk.NORMAL); self.cd.delete("1.0",tk.END)
        self.cd.config(state=tk.DISABLED); self._add_chat("welcome", self._welcome())

    def _up(self, s):
        icons = {"ok":"🟢","reason":"🧠","mcp":"🔌","evolve":"🧬","sys":"🖥️"}
        try: self.r.after(0, lambda: self.status_dot.config(text=icons.get(s,s)))
        except: pass

    def _on_close(self):
        self.r.destroy()
    def _quick_reason(self, mode):
        self._add_chat("user", f"[Reason:{mode}] Analyze project architecture")
        threading.Thread(target=self._do_reason,
                args=("Analyze the project architecture and potential improvements", mode),
                daemon=True).start()