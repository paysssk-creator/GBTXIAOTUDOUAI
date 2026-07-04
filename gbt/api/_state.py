"""GBT Pro · gbt/api/_state.py
──────────────────────────────────────────────
蓝图共享状态容器：webview 入口、DASH_HTML、DP 路径。
让 blueprint 模块可以访问主进程共享对象，避免循环依赖。
"""

# 开发者: 自由的风
from __future__ import annotations

import os

# pywebview 入口（由 desktop_app.py 注入；桌面启动时为真窗口对象，服务器模式为 None）
webview = None

# dashboard 模板路径与内容（在 desktop_app.py 启动时预读，blueprint 直接复用）
DP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "desktop", "templates", "layout.html",
)
STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "desktop", "templates",
)
DASH_HTML = ""
if os.path.exists(DP):
    try:
        # T-007-A 回滚：直接读 layout.html（_script_*.html 拆分的花括号配对有 bug）
        DASH_HTML = open(DP, "r", encoding="utf-8").read()
    except Exception:
        DASH_HTML = "<h1>GBT Pro</h1>"
else:
    DASH_HTML = "<h1>GBT Pro</h1>"


def set_webview(wv):
    """由 desktop_app.py 在启动时调用，注入 pywebview 引用"""
    global webview
    webview = wv


def get_webview():
    return webview