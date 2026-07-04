"""GBT Pro · gbt/api/dash.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：dash
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string, make_response
import os, json, time
from gbt.api import _state
from gbt.release_meta import runtime_identity
bp = Blueprint("dash", __name__)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    html = _state.DASH_HTML or "<h1>Dashboard not found</h1>"
    resp = make_response(render_template_string(html))
    resp.headers['Cache-Control']='no-cache,no-store,must-revalidate'
    resp.headers['Pragma']='no-cache'
    resp.headers['Expires']='0'
    return resp


@bp.route("/api/status")
def status():
    ident = runtime_identity()
    try:
        from gbt.providers import AutoKeyConfig
        from gbt.mcp import get_mcp
        discovered = AutoKeyConfig.scan()
        avail = sum(1 for v in discovered.values() if v["status"] == "available")
        return jsonify({"ok": True,
                       "role": ident["role"],
                       "version": ident["version"],
                       "release_tag": ident["release_tag"],
                       "mcp_count": len(get_mcp().list_servers()), "llm": "Akashic/DeepSeek/Ollama",
                       "model": "auto", "keys_available": avail, "keys_total": len(discovered)})
    except Exception:
        return jsonify({"ok": True, "role": ident["role"],
                        "version": ident["version"],
                        "release_tag": ident["release_tag"],
                        "mcp_count": 0, "llm": "N/A", "model": "N/A",
                        "keys_available": 0, "keys_total": 0})


@bp.route("/api/system")
def api_system():
    """真实系统指标 — 兼容 PyInstaller EXE 的 _MEIPASS 路径。"""
    import sys as _sys
    import shutil
    import psutil
    try:
        # EXE 包内 __file__ 解析到临时目录, 用 _MEIPASS 取真实盘
        if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
            disk_root = _sys._MEIPASS.split(":")[0] + ":\\"
        else:
            disk_root = "C:\\"
        if not os.path.exists(disk_root):
            disk_root = "C:\\"
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(disk_root).percent
        return jsonify({
            "cpu": round(cpu, 1),
            "memory": round(mem, 1),
            "disk": round(disk, 1),
            "host": os.environ.get("COMPUTERNAME", "") or os.uname().nodename if hasattr(os, "uname") else "",
            "uptime": round((time.time() - psutil.boot_time()) / 3600, 1),
            "ok": True
        })
    except Exception as e:
        return jsonify({"cpu": 0, "memory": 0, "disk": 0, "host": "", "uptime": 0, "ok": False, "error": str(e)[:50]})


@bp.route("/api/dashboard")
def dashboard_data():
    import psutil
    data = {}
    # LLM
    try:
        from gbt.llm_metrics import get_llm_metrics
        data["llm"] = get_llm_metrics()
    except Exception:
        data["llm"] = {
            "totals": {"tokens_total": 0, "cost_rmb": 0, "requests": 0},
            "current": {"model": "N/A", "provider": "N/A"},
            "history": []
        }
    # System
    try:
        import sys as _sys
        if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
            disk_root = _sys._MEIPASS.split(":")[0] + ":\\"
        else:
            disk_root = "C:\\"
        data["system"] = {
            "cpu": round(psutil.cpu_percent(interval=0.2), 1),
            "memory": round(psutil.virtual_memory().percent, 1),
            "disk": round(psutil.disk_usage(disk_root).percent, 1),
            "host": os.environ.get("COMPUTERNAME", "")
        }
    except Exception:
        data["system"] = {"cpu": 0, "memory": 0, "disk": 0, "host": ""}
    # MCP
    try:
        from gbt.mcp import get_mcp
        data["mcp"] = {"servers": get_mcp().list_servers()}
    except Exception:
        data["mcp"] = {"servers": []}
    # Trade / Account
    try:
        from gbt.paper_account import get_state as _pa_state
        pa = _pa_state()
        watchlist = [("600519", "贵州茅台"), ("600036", "招商银行")]
        watchlist_quotes = []
        # 优先复用 autopilot 最近一次扫描结果，避免 dashboard 请求阻塞在慢行情接口
        try:
            from gbt.autopilot import get_pilot
            sigs = {s.get("code"): s for s in get_pilot().state.get("signals", [])}
            for code, name in watchlist:
                s = sigs.get(code, {})
                watchlist_quotes.append({
                    "code": code,
                    "name": s.get("name") or name,
                    "price": round(s.get("price", 0) or 0, 2),
                    "change_pct": round(s.get("change_pct", 0) or 0, 2),
                })
        except Exception:
            watchlist_quotes = [{"code": c, "name": n, "price": 0, "change_pct": 0} for c, n in watchlist]
        data["trade"] = {
            "account": {
                "cash": round(pa.get("cash", 0), 2),
                "equity": round(pa.get("equity", 0), 2),
                "pnl": round(pa.get("total_pnl", 0), 2),
                "positions": pa.get("position_count", 0),
            },
            "watchlist": watchlist_quotes,
        }
    except Exception:
        data["trade"] = {
            "account": {"cash": 100000, "equity": 100000, "pnl": 0, "positions": 0},
            "watchlist": [
                {"code": "600519", "name": "贵州茅台", "price": 0, "change_pct": 0},
                {"code": "600036", "name": "招商银行", "price": 0, "change_pct": 0},
            ],
        }
    return jsonify(data)


@bp.route("/api/mcp/servers")
def api_mcp_servers():
    """MCP 服务器列表 — 给 MCP tab 用。"""
    try:
        from gbt.mcp import get_mcp
        servers = get_mcp().list_servers()
        return jsonify({
            "ok": True,
            "servers": servers,
            "count": len(servers),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:80], "servers": [], "count": 0}), 200


@bp.route("/styles.css")
def styles():
    sp = os.path.join(_state.STATIC_DIR, "styles.css")
    if os.path.exists(sp):return open(sp,"r",encoding="utf-8").read(),200,{"Content-Type":"text/css"}
    return "",404


@bp.route("/favicon.ico")
def favicon():return "",204

