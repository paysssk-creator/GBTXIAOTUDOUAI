# -*- coding: utf-8 -*-
"""
GBT小土豆 v8.0 — AI智能体 · 左侧科技面板 · 赛博风
"""
import os, sys, threading, time, re

if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT); sys.path.insert(0, ROOT)

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

from mirror_dimension.scanner import ProjectScanner
from mirror_dimension.auditor import ProjectAuditor
from mirror_dimension.fixer import SandboxFixer
from mirror_dimension.dimensions import DimensionTester
from mirror_dimension.mindmap_guide import get_guide, PIPELINE_GUIDES

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

LOGO = os.path.join(ROOT, "gbt_logo_32.png")

C = {
    "bg":"#080c14","panel":"#0d1320","card":"#111827","text":"#e0e8ff",
    "dim":"#5b6e9e","cyan":"#00e5ff","purple":"#a855f7","green":"#00e676",
    "red":"#ff3366","amber":"#ffb800","glow":"#0a1a30","border":"#1a2540",
    "user_bg":"#0a1a28","user_border":"#00e5ff","ai_bg":"#15102a","ai_border":"#a855f7",
}

PANEL_ITEMS = [
    ("🚀", "完整管道", "一键全流程验证", "full", C["cyan"]),
    ("🔍", "全量扫描", "危险代码·语法检查", "scan", C["purple"]),
    ("🔐", "深度审计", "敏感文件·密钥审计", "audit", C["purple"]),
    ("🔧", "沙盒修复", "自动修复→部署", "fix", C["purple"]),
    ("🎯", "四维度测试", "用户·开发·运维·安全", "dimensions", C["purple"]),
    ("🧠", "设计大脑", "思维导图·架构原则", "guide", C["purple"]),
]

INTENT_RULES = [
    (r"你好|hi|hello|嗨|在吗", "greet"),
    (r"能做什么|功能|能力|帮助|help", "help"),
    (r"扫描|检查.*代码|安全.*检查|scan", "scan"),
    (r"审计|安全.*审计|密钥|敏感文件|audit", "audit"),
    (r"修复|自动修复|修.*代码|fix", "fix"),
    (r"维度|评分|测试|四维度|dimension|test", "dimensions"),
    (r"完整|全流程|一键|全部.*跑|full|pipeline|管道", "full"),
    (r"设计.*脑|思维导图|指引|原则|guide|mindmap", "guide"),
    (r"切换.*(项目|路径|目录)|更换|浏览|browse|选择", "browse"),
    (r"当前.*项目|现在.*路径|在哪", "current"),
]

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GBT小土豆")
        self.geometry("900x720"); self.minsize(580, 460)
        self.configure(fg_color=C["bg"])
        self._path = ROOT; self._busy = False
        self._build(); self._center(); self._welcome()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        # ── 标题 ──
        hdr = ctk.CTkFrame(self, height=48, fg_color=C["panel"], corner_radius=0)
        hdr.pack(fill="x", side="top"); hdr.pack_propagate(False)
        if os.path.exists(LOGO):
            logo = ctk.CTkImage(light_image=Image.open(LOGO), size=(26, 26))
            ctk.CTkLabel(hdr, text="", image=logo).pack(side="left", padx=(16, 8))
        ctk.CTkLabel(hdr, text="GBT小土豆", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["cyan"]).pack(side="left")
        ctk.CTkLabel(hdr, text="AI 智能体", font=ctk.CTkFont(size=9),
                     text_color=C["dim"]).pack(side="left", padx=6)
        self._st = ctk.CTkLabel(hdr, text="● 在线", font=ctk.CTkFont(size=10), text_color=C["green"])
        self._st.pack(side="right", padx=16)
        ctk.CTkFrame(self, height=1, fg_color=C["glow"], corner_radius=0).pack(fill="x")

        # ── 主体 ──
        main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        main.pack(fill="both", expand=True)

        # ═══ 左侧科技面板 ═══
        sidebar = ctk.CTkFrame(main, width=190, fg_color=C["panel"], corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # 面板标题
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=40)
        title_frame.pack(fill="x", pady=(12, 4))
        title_frame.pack_propagate(False)
        ctk.CTkLabel(title_frame, text="◈  能力矩阵", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["cyan"]).pack(padx=14)

        # 每项：图标卡片
        for icon, name, desc, cmd, color in PANEL_ITEMS:
            card = ctk.CTkFrame(sidebar, fg_color=C["card"], corner_radius=8,
                               border_width=1, border_color=C["border"])
            card.pack(fill="x", padx=8, pady=3)
            ctk.CTkButton(card, text=f"{icon}  {name}", font=ctk.CTkFont(size=10, weight="bold"),
                         fg_color="transparent", text_color=color,
                         hover_color=C["glow"], corner_radius=6,
                         anchor="w", height=32, command=lambda c=cmd: self._trigger(c)
                         ).pack(fill="x", padx=4, pady=2)

        # ── 服务登录区域 ──
        ctk.CTkFrame(sidebar, fg_color="transparent", height=8).pack(fill="x")
        svc_title = ctk.CTkFrame(sidebar, fg_color="transparent", height=36)
        svc_title.pack(fill="x", pady=(6, 2))
        svc_title.pack_propagate(False)
        ctk.CTkLabel(svc_title, text="◈  服务登录", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["cyan"]).pack(padx=14)

        # 服务列表
        import subprocess as _sp
        _r = _sp.run(["gh", "auth", "status"], capture_output=True, timeout=5)
        self._gh_ok = _r.returncode == 0

        services = [
            ("🐙", "GitHub", lambda: self._gh_ok, self._github_login),
            ("🦊", "GitLab", lambda: getattr(self, '_gl_ok', False), self._gitlab_login),
            ("🐴", "Gitee", lambda: getattr(self, '_gitee_ok', False), self._gitee_login),
        ]
        for icon, name, check, login in services:
            row = ctk.CTkFrame(sidebar, fg_color="transparent", height=34)
            row.pack(fill="x", padx=8, pady=1)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=13), width=26).pack(side="left")
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=C["text"], width=48).pack(side="left")
            authed = check()
            ctk.CTkLabel(row, text="已连接" if authed else "未连接",
                         font=ctk.CTkFont(size=9),
                         text_color=C["green"] if authed else C["dim"],
                         width=48).pack(side="left")
            btn_text = "断开" if authed else "连接"
            btn_color = C["border"] if authed else C["cyan"]
            btn_cmd = (lambda n=name: self._disconnect(n)) if authed else login
            btn = ctk.CTkButton(row, text=btn_text, font=ctk.CTkFont(size=9),
                                fg_color=btn_color, text_color=C["text"] if authed else C["bg"],
                                hover_color=C["red"] if authed else "#00c8e0",
                                corner_radius=5, height=22, width=42,
                                command=btn_cmd)
            btn.pack(side="right", padx=2)

        # 浏览仓库
        any_ok = self._gh_ok or getattr(self, '_gl_ok', False) or getattr(self, '_gitee_ok', False)
        self._repo_btn = ctk.CTkButton(sidebar, text="📦 浏览仓库", font=ctk.CTkFont(size=10),
                                       fg_color="transparent", text_color=C["dim"],
                                       hover_color=C["border"], corner_radius=6,
                                       height=26, command=self._browse_repos,
                                       state="normal" if any_ok else "disabled")
        self._repo_btn.pack(fill="x", padx=8, pady=(6, 12))


        # ═══ 聊天区 ═══
        self._chat = ctk.CTkScrollableFrame(main, fg_color=C["bg"], corner_radius=0)
        self._chat.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # ── 输入 ──
        inp = ctk.CTkFrame(self, height=60, fg_color=C["panel"], corner_radius=0,
                           border_width=1, border_color=C["border"])
        inp.pack(fill="x", side="bottom"); inp.pack_propagate(False)
        self._entry = ctk.CTkTextbox(inp, font=ctk.CTkFont(size=13),
                                     fg_color=C["card"], text_color=C["text"],
                                     border_width=1, border_color=C["border"],
                                     wrap="word", height=38, corner_radius=10)
        self._entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=11)
        self._entry.bind("<Return>", self._on_enter)
        self._btn = ctk.CTkButton(inp, text="▶", font=ctk.CTkFont(size=14, weight="bold"),
                                  width=38, height=38, corner_radius=19,
                                  fg_color=C["cyan"], text_color=C["bg"],
                                  hover_color="#00c8e0", command=self._send)
        self._btn.pack(side="right", padx=(0, 16))

    # ═══ 气泡 ═══
    def _user_bubble(self, text):
        row = ctk.CTkFrame(self._chat, fg_color="transparent")
        row.pack(fill="x", pady=(8, 2))
        bubble = ctk.CTkFrame(row, fg_color=C["user_bg"], corner_radius=14,
                              border_width=1, border_color=C["user_border"])
        bubble.pack(side="right", padx=16)
        ctk.CTkLabel(bubble, text=" "+text.replace("\n", "\n ")+" ",
                     font=ctk.CTkFont(size=11), text_color=C["cyan"],
                     wraplength=440, justify="left").pack(padx=12, pady=10)
        self._chat._parent_canvas.yview_moveto(1.0)

    def _bot_bubble(self, text):
        row = ctk.CTkFrame(self._chat, fg_color="transparent")
        row.pack(fill="x", pady=(6, 2))
        if os.path.exists(LOGO):
            img = ctk.CTkImage(light_image=Image.open(LOGO), size=(24, 24))
            ctk.CTkLabel(row, text="", image=img, width=30, height=30).pack(side="left", padx=(16, 8))
        bubble = ctk.CTkFrame(row, fg_color=C["ai_bg"], corner_radius=14,
                              border_width=1, border_color=C["ai_border"])
        bubble.pack(side="left")
        ctk.CTkLabel(bubble, text=" "+text.replace("\n", "\n ")+" ",
                     font=ctk.CTkFont(size=11), text_color=C["text"],
                     wraplength=420, justify="left").pack(padx=12, pady=10)
        self._chat._parent_canvas.yview_moveto(1.0)

    # ═══ 欢迎 ═══
    def _welcome(self):
        self._bot_bubble("✦ GBT小土豆 AI 智能体 已就绪 ✦\n\n我可以通过对话帮你完成项目安全验证。\n\n▸ 直接打字或点选左侧能力面板\n▸ 输入「完整管道」一键跑完全流程\n▸ 输入「帮助」查看更多功能")
        self._bot_bubble(f"◇ 当前项目：{self._path}")

    # ═══ 触发能力面板 ═══
    def _trigger(self, mode):
        label = [k for k, v in PANEL_ITEMS if v[3] == mode][0]
        self._user_bubble(label)
        if mode in ("scan","audit","fix","full","dimensions"):
            self._run_task(mode)
        elif mode == "guide":
            g = get_guide(mode)
            self._bot_bubble(f"🧠 {g['title']}\n\n{g['principle'].strip()[:400]}\n\n◇ {g['source']}")

    # ═══ 发送 ═══
    def _on_enter(self, ev):
        if not ev.state & 1: self._send(); return "break"

    def _send(self):
        if self._busy: return
        t = self._entry.get("1.0", "end-1c").strip()
        if not t: return
        self._entry.delete("1.0", "end")
        self._user_bubble(t)
        for pat, intent in INTENT_RULES:
            if re.search(pat, t, re.I):
                if intent in ("greet","help","current"):
                    return self._smart_reply(intent)
                if intent == "browse":
                    d = filedialog.askdirectory(initialdir=self._path)
                    if d: self._path = d; self._bot_bubble(f"✓ 已切换至：{d}")
                    return
                if intent == "guide":
                    g = get_guide()
                    self._bot_bubble(f"🧠 {g['title']}\n\n{g['principle'].strip()[:400]}\n\n◇ {g['source']}")
                    return
                if intent in ("scan","audit","fix","full","dimensions"):
                    return self._run_task(intent)
        self._bot_bubble("不太理解 😅\n试试：扫描项目 / 安全审计 / 完整管道 / 帮助")

    def _smart_reply(self, intent):
        replies = {
            "greet": "✦ 你好！试试跟我说「扫描项目」或「完整管道」吧～",
            "help": "✦ 能力列表 ✦\n\n🔍 扫描 · 🔐 审计 · 🔧 修复\n🎯 四维度测试 · 🚀 完整管道\n🧠 设计大脑 · 📁 切换项目\n\n右侧面板可直接点击，也可在对话框输入。",
            "current": f"◇ 当前项目：{self._path}\n▸ 输入「切换项目」可更改。",
        }
        self._bot_bubble(replies.get(intent, ""))

    def _run_task(self, mode):
        self._busy = True; self._st.configure(text="● 执行中", text_color=C["amber"])
        threading.Thread(target=self._run, args=(mode,), daemon=True).start()

    def _run(self, mode):
        t0 = time.time()
        try:
            self.after(0, lambda: self._bot_bubble("▹ 正在执行..."))
            s = ProjectScanner(self._path).scan()
            dangers = s.get("dangers",0); synerrs = s.get("syntax_errors",0)
            clean = (dangers + synerrs) == 0
            self.after(0, lambda: self._bot_bubble(
                "◈ 扫描 " + str(s["total_files"]) + "文件 · " + ("✓ 通过" if clean else "✕ " + str(dangers) + "危险+" + str(synerrs) + "错误")))
            if mode == "scan": return self._done(t0, s)

            a = ProjectAuditor(self._path).audit()
            ac = a.get("clean", False)
            self.after(0, lambda: self._bot_bubble(
                "◈ 审计 · " + ("✓ 通过" if ac else "✕ " + str(len(a.get("sensitive_files",[]))) + "个敏感文件")))
            if mode == "audit": return self._done(t0, s, a)

            f = SandboxFixer(self._path).run()
            fc = f.get("clean", False)
            self.after(0, lambda: self._bot_bubble(
                "◈ 修复 " + str(f.get("fixes_applied",0)) + "处 · 部署" + str(f.get("deployed",0)) + "文件 · " + ("✓ 通过" if fc else "✕")))
            if mode == "fix": return self._done(t0, s, a, f)

            d = DimensionTester(self._path).test()
            self.after(0, lambda dd=d: self._bot_bubble("◈ 四维度 " + str(dd["average_score"]) + "/20 · " + dd["verdict"]))
            return self._done(t0, s, a, f, d)
        except Exception as e:
            self.after(0, lambda: self._bot_bubble(f"✕ 出错: {e}"))
        finally:
            self._busy = False; self.after(0, lambda: self._st.configure(text="● 在线", text_color=C["green"]))

    def _done(self, t0, s, a=None, f=None, d=None):
        sec = round(time.time()-t0, 1)
        lines = [f"◆ 完成 · {sec}s", f"◇ {s['total_files']}文件 · 危险{s.get('dangers',0)} · 虚假{s.get('fakes',0)}"]
        if d:
            lines.append(f"◇ {d['average_score']}/20 · {d['verdict']}")
            for k, lb in [("user","👤用户"),("developer","💻开发"),("ops","⚙️运维"),("security","🛡️安全")]:
                ss=d.get(k,{}).get("score",0)
                lines.append(f"  {lb} {'█'*ss}{'░'*(20-ss)} {ss}/20")
        ok = s.get("dangers",0)==0 and s.get("syntax_errors",0)==0
        if d: ok = ok and d.get("average_score",0)>=12
        lines.append("✓ 全部通过" if ok else "✕ 需关注")
        self.after(0, lambda: self._bot_bubble("\n".join(lines)))

    # ═══ 通用 OAuth 本地服务器 ═══
    OAUTH_PORT = 19763

    def _start_oauth_server(self, platform, state):
        """启动本地 HTTP 服务器，等待 OAuth 回调"""
        import http.server, urllib.parse as _up
        app = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = _up.urlparse(self.path)
                params = _up.parse_qs(parsed.query)
                if platform == "gitee":
                    # Gitee 在查询参数中返回 code
                    code = params.get("code", [None])[0]
                else:
                    code = params.get("code", [None])[0]
                got_state = params.get("state", [None])[0]
                if code and got_state == state:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("<h2>授权成功！</h2><p>正在返回 GBT小土豆...</p><script>setTimeout(()=>window.close(),800)</script>".encode())
                    app.after(0, lambda: app._oauth_callback(platform, code))
                else:
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b"Invalid callback")
                self.server.auth_done = True
            def log_message(self, *args): pass

        srv = http.server.HTTPServer(("localhost", self.OAUTH_PORT), Handler)
        srv.auth_done = False
        def _serve():
            while not srv.auth_done:
                srv.handle_request()
            srv.server_close()
        threading.Thread(target=_serve, daemon=True).start()

    def _oauth_callback(self, platform, code):
        threading.Thread(target=self._exchange_token, args=(platform, code), daemon=True).start()

    def _exchange_token(self, platform, code):
        """用授权码交换 access_token"""
        import urllib.parse as _up, json as _json, urllib.request
        try:
            if platform == "gitlab":
                data = _up.urlencode({
                    "client_id": self.GITLAB_CLIENT_ID,
                    "client_secret": self.GITLAB_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"http://localhost:{self.OAUTH_PORT}/callback",
                }).encode()
                req = urllib.request.Request("https://gitlab.com/oauth/token", data=data)
                resp = _json.loads(urllib.request.urlopen(req, timeout=15).read())
                if resp.get("access_token"):
                    self._gl_ok = True
                    self.after(0, lambda: (self._bot_bubble("✓ GitLab 已连接"), self._refresh_services()))
            elif platform == "gitee":
                data = _up.urlencode({
                    "client_id": self.GITEE_CLIENT_ID,
                    "client_secret": self.GITEE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"http://localhost:{self.OAUTH_PORT}/callback",
                }).encode()
                req = urllib.request.Request("https://gitee.com/oauth/token", data=data,
                                             headers={"Content-Type": "application/x-www-form-urlencoded"})
                resp = _json.loads(urllib.request.urlopen(req, timeout=15).read())
                if resp.get("access_token"):
                    self._gitee_ok = True
                    self.after(0, lambda: (self._bot_bubble("✓ Gitee 已连接"), self._refresh_services()))
        except Exception as e:
            self.after(0, lambda: self._bot_bubble("✕ 授权失败: " + str(e)[:100]))

    # ═══ 服务登录 ═══
    GITHUB_CLIENT_ID = "Iv1.b507a08c87ecf98c"
    GITLAB_CLIENT_ID = "c692cc14f6cefb105cf50edea659d08ab35f36adf088ad3ed9b6c2aa0d53a2d9"
    GITLAB_CLIENT_SECRET = "gloas-f37777fad7e20fefd6198016047be87f548a265c828b78158f9e336b08ecad96"
    GITEE_CLIENT_ID = "253b0ebeae13e58dcbd43409217cac0e117508958c049b956a85e587d8d45906"
    GITEE_CLIENT_SECRET = "cf49ad5c391c7c5e27a123362ea4f67b2c7da5235cb17314ed8f6d9a65ebacf6"

    def _github_login(self):
        import subprocess, json as _json, urllib.request, secrets
        # 用 Device Flow
        req_data = _json.dumps({
            "client_id": self.GITHUB_CLIENT_ID,
            "scope": "repo read:user",
        }).encode()
        req = urllib.request.Request("https://github.com/login/device/code",
                                     data=req_data, headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        resp = _json.loads(urllib.request.urlopen(req, timeout=15).read())
        device_code = resp["device_code"]
        user_code = resp["user_code"]
        verify_url = resp["verification_uri"]
        interval = int(resp.get("interval", 5))

        self._bot_bubble(f"🐙 GitHub 授权\n\n▸ 浏览器已打开验证页面\n▸ 输入验证码：{user_code}\n▸ 点击授权 → 自动完成")
        os.startfile(verify_url)

        def _poll():
            poll_data = _json.dumps({
                "client_id": self.GITHUB_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }).encode()
            for _ in range(24):
                time.sleep(interval)
                pr = urllib.request.Request("https://github.com/login/oauth/access_token",
                                            data=poll_data, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                })
                result = _json.loads(urllib.request.urlopen(pr, timeout=15).read())
                if "access_token" in result:
                    tok = result["access_token"]
                    subprocess.run(["gh", "auth", "login", "--with-token"],
                                   input=tok.encode(), timeout=15)
                    self._gh_ok = True
                    self._repo_btn.configure(state="normal")
                    self._bot_bubble("✓ GitHub 已连接")
                    return
                if result.get("error") != "authorization_pending":
                    break
            self._bot_bubble("✕ GitHub 授权超时，请重试")
        threading.Thread(target=_poll, daemon=True).start()

    def _gitlab_login(self):
        """GitLab OAuth 全自动授权"""
        import urllib.parse, secrets
        state = secrets.token_urlsafe(16)
        params = urllib.parse.urlencode({
            "client_id": self.GITLAB_CLIENT_ID,
            "redirect_uri": f"http://localhost:{self.OAUTH_PORT}/callback",
            "response_type": "code",
            "scope": "api read_user read_repository",
            "state": state,
        })
        url = f"https://gitlab.com/oauth/authorize?{params}"
        self._bot_bubble("🦊 GitLab 授权\n\n▸ 浏览器已打开 GitLab 授权页\n▸ 登录并授权 → 自动跳回完成")
        self._start_oauth_server("gitlab", state)
        os.startfile(url)

    def _gitee_login(self):
        """Gitee OAuth 全自动授权"""
        import urllib.parse, secrets
        state = secrets.token_urlsafe(16)
        params = urllib.parse.urlencode({
            "client_id": self.GITEE_CLIENT_ID,
            "redirect_uri": f"http://localhost:{self.OAUTH_PORT}/callback",
            "response_type": "code",
            "scope": "user_info projects",
            "state": state,
        })
        url = f"https://gitee.com/oauth/authorize?{params}"
        self._bot_bubble("🐴 Gitee 授权\n\n▸ 浏览器已打开 Gitee 授权页\n▸ 登录并授权 → 自动跳回完成")
        self._start_oauth_server("gitee", state)
        os.startfile(url)

    def _refresh_services(self):
        """刷新左侧面板的服务连接状态"""
        any_ok = False
        for name, check, login, status_lbl, btn in self._svc_widgets:
            authed = check()
            if authed:
                any_ok = True
            status_lbl.configure(text="已连接" if authed else "未连接",
                               text_color=C["green"] if authed else C["dim"])
            btn.configure(text="断开" if authed else "连接",
                         fg_color=C["border"] if authed else C["cyan"],
                         text_color=C["text"] if authed else C["bg"],
                         hover_color=C["red"] if authed else "#00c8e0",
                         command=(lambda n=name: self._disconnect(n)) if authed else login)
        self._repo_btn.configure(state="normal" if any_ok else "disabled")

    def _disconnect(self, platform):
        if platform == "GitHub":
            import subprocess as _sp
            _sp.run(["gh", "auth", "logout"], capture_output=True, timeout=5)
            self._gh_ok = False
        elif platform == "GitLab":
            self._gl_ok = False
        elif platform == "Gitee":
            self._gitee_ok = False
        self._bot_bubble(f"✕ {platform} 已断开")
        self._refresh_services()

    def _start_clipboard_poll(self):
        self._clip_last = ""
        self._clip_count = 0
        self._clipboard_tick()

    def _clipboard_tick(self):
        if not hasattr(self, '_pending_auth') or not self._pending_auth:
            return
        self._clip_count += 1
        if self._clip_count > 120:
            self._bot_bubble("✕ 授权超时，请重试")
            self._pending_auth = None
            return
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT) or \
               win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                try:
                    clip = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except Exception:
                    clip = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
            else:
                clip = ""
            win32clipboard.CloseClipboard()
            if clip and clip != self._clip_last:
                self._clip_last = clip
                for t in clip.strip().split():
                    if len(t) > 15:
                        if self._handle_token(t):
                            return
        except Exception:
            try: win32clipboard.CloseClipboard()
            except Exception: pass
        self.after(1000, self._clipboard_tick)

    def _handle_token(self, token_str):
        if not hasattr(self, '_pending_auth') or not self._pending_auth:
            return False
        platform = self._pending_auth
        token = token_str.strip()

        import subprocess, json as _json, urllib.request

        if platform == "gitlab":
            req = urllib.request.Request("https://gitlab.com/api/v4/user",
                                         headers={"PRIVATE-TOKEN": token})
            try:
                resp = _json.loads(urllib.request.urlopen(req, timeout=10).read())
                user = resp.get("username", "unknown")
                subprocess.run(["git", "config", "--global", "gbt.gitlab.token", token],
                              capture_output=True, timeout=5)
                self._gl_ok = True; self._pending_auth = None
                self.after(0, lambda u=user: (self._bot_bubble("✓ GitLab 已连接 · " + u), self._refresh_services()))
                return True
            except Exception:
                return False

        elif platform == "gitee":
            req = urllib.request.Request(f"https://gitee.com/api/v5/user?access_token={token}")
            try:
                resp = _json.loads(urllib.request.urlopen(req, timeout=10).read())
                user = resp.get("login", "unknown")
                subprocess.run(["git", "config", "--global", "gbt.gitee.token", token],
                              capture_output=True, timeout=5)
                self._gitee_ok = True; self._pending_auth = None
                self.after(0, lambda u=user: (self._bot_bubble("✓ Gitee 已连接 · " + u), self._refresh_services()))
                return True
            except Exception:
                return False
        return False

    def _browse_repos(self):
        self._bot_bubble("📦 请在对话框粘贴仓库链接，我会自动克隆分析。\n如：https://github.com/user/repo")

if __name__ == "__main__":
    App().mainloop()
