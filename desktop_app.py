"""GBT Pro — AI驱动A股自主交易终端 · Desktop App (pywebview)"""

# 开发者: 自由的风
import os, sys, json, time, threading, logging, platform, re

# ── 加载 .env 环境变量 · 多级回退（PyInstaller 兼容） ──
try:
    from dotenv import load_dotenv
    import sys as _sys

    def _find_env():
        """查找 .env。

        默认只认当前工作目录 / exe 同级 / _MEIPASS，避免冻结包在用户机器上
        偷偷捡到父目录配置，形成“你机器能跑、用户机器不行”的假象。

        仅在显式设置 GBT_ALLOW_PARENT_ENV_SEARCH=true 时，才向上回退父目录。
        """
        import os as _os
        roots = [
            _os.getcwd(),
            _os.path.dirname(_os.path.abspath(_sys.executable if getattr(_sys, 'frozen', False) else __file__)),
            getattr(_sys, '_MEIPASS', _os.path.dirname(__file__)),
        ]
        allow_parent = _os.environ.get("GBT_ALLOW_PARENT_ENV_SEARCH", "").strip().lower() in ("1", "true", "yes", "on")
        seen = set()
        candidates = []
        for root in roots:
            cur = _os.path.abspath(root)
            max_depth = 6 if allow_parent else 1
            for _ in range(max_depth):
                env_candidate = _os.path.join(cur, ".env")
                if env_candidate not in seen:
                    candidates.append(env_candidate)
                    seen.add(env_candidate)
                parent = _os.path.dirname(cur)
                if not parent or parent == cur:
                    break
                cur = parent
        for p in candidates:
            if _os.path.isfile(p):
                return p
        return None

    env_path = _find_env()
    if env_path:
        load_dotenv(env_path)
        os.environ.setdefault("GBT_PROJECT_ROOT", os.path.dirname(env_path))
        loaded = sum(1 for k in ("DEEPSEEK_API_KEY", "FUTURAPAY_SITE_ID", "FUTURAPAY_API_KEY_LOCAL", "FUTURAPAY_MERCHANT_KEY")
                     if os.getenv(k))
        print(f"[ENV] .env loaded from {env_path} · {loaded} secret field(s) present")
    else:
        print("[ENV] No .env found in cwd / exe dir / _MEIPASS. Set GBT_ALLOW_PARENT_ENV_SEARCH=true only for legacy local bootstrap.")
except ImportError:
    print("[ENV] python-dotenv not installed — using os.environ only")
except Exception as e:
    print(f"[ENV] Load warning: {e}")

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "desktop"))
try:
    import webview
except Exception:
    webview = None  # 仅在桌面启动时使用；服务器模式下为 None
from gbt.api import _state  # 共享状态容器
from flask import Flask,render_template_string,jsonify,request

# PyInstaller 兼容的模板路径
def _resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 加载 layout.html（PyInstaller 兼容
def _find_layout():
    candidates = [
        os.path.join(os.path.dirname(__file__),"desktop","templates","layout.html"),  # 开发模式
        os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), "templates", "layout.html"),  # PyInstaller 模式
        os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "templates", "layout.html"),  # 解压后的 exe 同级
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

DP = _find_layout()
if DP:
    DASH_HTML = open(DP, "r", encoding="utf-8").read()
else:
    DASH_HTML = "<h1>GBT Pro - 模板未找到</h1><p>请检查 templates 文件夹</p>"
from gbt.knowledge.inject import inject_knowledge
inject_knowledge()

# PyInstaller 模式下配置正确的 template 和 static 路径
if getattr(sys, 'frozen', False):
    # 优先找 exe 同级的 templates（方便用户自行修改），没有则用 _MEIPASS
    exe_dir = os.path.dirname(sys.executable)
    candidate = os.path.join(exe_dir, 'templates')
    if os.path.exists(candidate):
        template_dir = candidate
        static_dir = candidate
    else:
        template_dir = os.path.join(sys._MEIPASS, 'templates')
        static_dir = os.path.join(sys._MEIPASS, 'templates')
else:
    template_dir = os.path.join(os.path.dirname(__file__), 'desktop', 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'desktop', 'templates')

print(f"[Flask] template_folder={template_dir}, exists={os.path.exists(template_dir)}")
print(f"[Flask] static_folder={static_dir}, exists={os.path.exists(static_dir)}")
print(f"[Flask] layout_path={DP}, exists={bool(DP and os.path.exists(DP))}")

# 关键修复：蓝图 `/dashboard` 读取的是共享状态 `_state.DASH_HTML`，打包模式下必须由入口注入真实模板。
_state.DP = DP or ""
_state.STATIC_DIR = static_dir
_state.DASH_HTML = DASH_HTML

app=Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/')

# ── 注册全部 13 个 blueprint（按子域拆分自原 desktop_app.py） ──
from gbt.api import register_all  # noqa: E402
_state.set_webview(webview)
mounted = register_all(app)
print(f"[API] mounted {len(mounted)} blueprints: {', '.join(mounted)}")


if __name__=="__main__":
    # ── 日志配置（--noconsole 模式下写文件） ──
    log_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    log_file = os.path.join(log_dir, "gbt_app.log")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
                        handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()])
    log = logging.getLogger()

    def log_print(msg):
        print(msg)
        log.info(msg)

    log_print("=" * 60)
    log_print("GBT Pro — AI驱动A股自主交易终端")
    log_print("=" * 60)

    # ── 启动 Flask 服务器（后台） ──
    threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False,threaded=True),daemon=True).start()
    time.sleep(3)

    # ── 自主操盘自动启动 ──
    try:
        from gbt.autopilot import get_pilot
        get_pilot().start()
        log_print("[AUTOPILOT] Auto-started")
    except Exception as e:
        log_print(f"[AUTOPILOT] Auto-start skipped: {e}")

    # ── 桌面窗口：优先 pywebview，失败 fallback 到浏览器 ──
    dashboard_url = "http://127.0.0.1:8765/dashboard"
    use_webview = True

    if webview:
        try:
            log_print("[UI] Starting pywebview window...")
            webview.create_window("GBT Pro — 自主操盘·AI智能交易终端", dashboard_url, width=1280, height=800, min_size=(1000, 650))
            webview.start()
        except Exception as e:
            log_print(f"[UI] pywebview failed: {e}")
            use_webview = False
    else:
        log_print("[UI] pywebview not available")
        use_webview = False

    if not use_webview:
        log_print("[UI] Falling back to default browser...")
        import webbrowser
        webbrowser.open(dashboard_url)
        # 保持进程不退出（如果是浏览器模式）
        while True:
            time.sleep(1)
