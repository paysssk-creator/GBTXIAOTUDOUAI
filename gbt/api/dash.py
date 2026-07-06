"""GBT Pro · gbt/api/dash.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：dash
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string, make_response
import os, json, time, re
from gbt.api import _state
from gbt.release_meta import runtime_identity
bp = Blueprint("dash", __name__)


_BROWSER_WINDOW_RE = re.compile(r"(chrome|edge|firefox|浏览器|webview)", re.I)


def _parse_amount(value):
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("¥", "").replace("￥", "").replace(",", "").strip()
    m = re.search(r"([+-]?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return round(float(m.group(1)), 2)
    except Exception:
        return None


def _extract_labeled_amount(text, labels):
    content = str(text or "")
    for label in labels:
        pattern = rf"(?:{label})[：:\s¥￥]*([+-]?\d[\d,]*(?:\.\d+)?)"
        m = re.search(pattern, content)
        if m:
            amount = _parse_amount(m.group(1))
            if amount is not None:
                return amount
    return None


def _empty_live_account(reason="", broker="", window_state=None):
    return {
        "cash": None,
        "equity": None,
        "pnl": None,
        "positions": 0,
        "connected": False,
        "source": "unavailable",
        "reason": reason,
        "broker": broker or None,
        "window_state": window_state or {},
        "updated_at": "",
    }


def _live_account_from_screen():
    try:
        from gbt.api.audit import _scan_broker_windows
        scan = _scan_broker_windows()
        broker_hits = scan.get("broker_windows") or []
        selected = None
        for item in broker_hits:
            title = str((item or {}).get("title") or "").strip()
            if title and not _BROWSER_WINDOW_RE.search(title):
                selected = item
                break
        if not selected:
            return _empty_live_account(reason="未识别到真实券商客户端窗口", window_state=scan)

        active_title = str(((scan.get("active_window") or {}).get("title")) or "").strip()
        selected_title = str(selected.get("title") or "").strip()
        broker_name = str(selected.get("broker") or "").strip()
        if not active_title or active_title != selected_title:
            return _empty_live_account(reason="真实券商客户端未在前台", broker=broker_name, window_state=scan)

        from gbt.screen_ai import ScreenOCR
        ocr = ScreenOCR()
        result = ocr.read_text()
        if not result.get("ok"):
            return _empty_live_account(reason=result.get("error", "账户OCR读取失败"), broker=broker_name, window_state=scan)

        text = result.get("text") or ""
        cash = _extract_labeled_amount(text, ["可用资金", "可用余额", "资金余额", "可取资金", "可取金额"])
        equity = _extract_labeled_amount(text, ["总资产", "资产总值", "账户资产", "总权益", "净资产", "净值"])
        pnl = _extract_labeled_amount(text, ["参考盈亏", "浮动盈亏", "总盈亏", "当日盈亏", "盈亏"])
        position_state = ocr.detect_trade_panel_readback(panel="position", broker=broker_name)
        positions = int(((position_state.get("summary") or {}).get("row_count")) or 0)
        if not positions:
            positions = len(position_state.get("rows") or [])

        has_asset_labels = sum(1 for key in ("可用资金", "总资产", "资产总值", "账户资产", "参考盈亏", "浮动盈亏") if key in text)
        connected = (cash is not None) or (equity is not None) or (has_asset_labels >= 2 and pnl is not None)
        if not connected:
            return _empty_live_account(reason="已聚焦券商客户端，但未回读到账户资金区", broker=broker_name, window_state=scan)

        return {
            "cash": cash,
            "equity": equity,
            "pnl": pnl,
            "positions": positions,
            "connected": True,
            "source": "broker_ocr",
            "reason": "",
            "broker": broker_name or None,
            "window_state": scan,
            "updated_at": result.get("timestamp") or "",
        }
    except Exception as e:
        return _empty_live_account(reason=str(e)[:120])


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
        live_account = _live_account_from_screen()
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
            "account": live_account,
            "watchlist": watchlist_quotes,
        }
    except Exception:
        data["trade"] = {
            "account": _empty_live_account(reason="账户快照读取失败"),
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

