"""GBT Pro · gbt/api/desktop.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：desktop
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time, sys
from pathlib import Path
from gbt.api.audit import _exec_desktop, _exec_system_status
from gbt.control_stack import build_control_stack_report
bp = Blueprint("desktop", __name__)


_DESKTOP_ACTIONS = [
    {"id": "system_status", "name": "系统状态", "desc": "读取当前系统与桌面运行状态"},
    {"id": "screenshot", "name": "屏幕截图", "desc": "抓取当前桌面截图并保存证据"},
    {"id": "browser_open", "name": "打开浏览器", "desc": "打开系统默认浏览器"},
    {"id": "broker_open", "name": "打开券商", "desc": "按券商名称打开交易或行情入口"},
    {"id": "broker_list", "name": "券商列表", "desc": "列出可用券商与行情平台"},
    {"id": "broker_login_detect", "name": "登录检测", "desc": "OCR检测当前券商是否已登录"},
    {"id": "broker_window_scan", "name": "券商窗口扫描", "desc": "识别当前系统中的券商相关窗口"},
    {"id": "broker_window_focus", "name": "券商窗口聚焦", "desc": "将指定券商窗口切到前台"},
    {"id": "trade_ready_check", "name": "操盘准备检查", "desc": "检查券商窗口与登录状态是否就绪"},
    {"id": "trade_takeover_ready", "name": "自主接管准备", "desc": "自动聚焦券商并判断 AI 是否可接管操盘"},
    {"id": "trade_takeover_watch", "name": "持续接管监视", "desc": "持续等待券商窗口与登录完成，并自动尝试切到交易页"},
    {"id": "trade_takeover_precheck", "name": "接管后预检", "desc": "串联接管状态、填单条件和高风险门禁，给出下一步动作建议"},
    {"id": "trade_anchor_detect", "name": "交易锚点识别", "desc": "OCR识别代码/价格/数量输入框与确认按钮锚点"},
    {"id": "trade_confirm_detect", "name": "确认弹窗识别", "desc": "识别交易确认弹窗与确认按钮位置"},
    {"id": "trade_entrust_readback", "name": "委托区域回读", "desc": "OCR回读当前委托列表摘要"},
    {"id": "trade_position_readback", "name": "持仓区域回读", "desc": "OCR回读当前持仓列表摘要"},
    {"id": "trade_panel_probe", "name": "联合回读探测", "desc": "聚焦券商窗口后联合回读委托区与持仓区"},
    {"id": "trade_submit_confirm", "name": "提交交易确认", "desc": "在人工确认后点击交易确认按钮"},
    {"id": "trade_result_watch", "name": "委托结果回看", "desc": "OCR回看委托提交/成交结果"},
    {"id": "trade_workflow", "name": "操盘流程", "desc": "统一执行打开券商、登录检测和看盘准备"},
    {"id": "window_maximize", "name": "窗口最大化", "desc": "最大化当前窗口"},
    {"id": "keyboard_type", "name": "键盘输入", "desc": "向当前焦点窗口输入文字"},
    {"id": "keyboard_hotkey", "name": "键盘快捷键", "desc": "触发常用快捷键组合"},
    {"id": "mouse_click", "name": "鼠标点击", "desc": "执行当前鼠标点击动作"},
    {"id": "mouse_move", "name": "鼠标移动", "desc": "将鼠标移动到指定位置"},
    {"id": "process_list", "name": "进程列表", "desc": "列出当前运行进程"},
    {"id": "process_kill", "name": "结束进程", "desc": "结束指定进程"},
    {"id": "window_focus", "name": "聚焦窗口", "desc": "切换前台焦点窗口"},
    {"id": "volume_control", "name": "音量调节", "desc": "调节系统音量"},
    {"id": "trade_form_fill", "name": "交易填单", "desc": "向当前交易表单填写代码、价格与手数"},
    {"id": "system_lock", "name": "锁屏", "desc": "锁定当前系统桌面"},
]


def _ui_safe_path(raw: str) -> str:
    path = Path(str(raw or ""))
    try:
        base = Path.cwd().resolve() if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
        rel = path.resolve().relative_to(base)
        prefix = "[runtime]/" if getattr(sys, "frozen", False) else "[project]/"
        return prefix + str(rel).replace("\\", "/")
    except Exception:
        return path.name or "[path]"


def _sanitize_ui_text(text: str) -> str:
    text = str(text or "")
    tokens = text.replace("\r", "\n").split()
    for token in tokens:
        candidate = token.strip("()[]{}<>'\",;")
        if len(candidate) > 3 and candidate[1:3] == ":\\":
            text = text.replace(candidate, _ui_safe_path(candidate))
    return text


def _sanitize_ui_payload(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key == "path" and isinstance(item, str):
                cleaned[key] = _ui_safe_path(item)
            else:
                cleaned[key] = _sanitize_ui_payload(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_ui_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_ui_text(value)
    return value


@bp.route("/api/url_scheme")
def api_url_scheme():return jsonify({"ok":True})


@bp.route("/api/desktop/snapshot")
def api_desktop_snapshot():
    """真实桌面快照 — 屏幕分辨率 / 鼠标位置 / 当前焦点窗口（如果有 win32gui）。"""
    snap = {"ok": True, "screen": {}, "mouse": {}, "window": {}, "errors": []}
    try:
        import ctypes
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        snap["screen"] = {"width": sw, "height": sh, "ratio": round(sw / sh, 3) if sh else 0}
    except Exception as e:
        snap["errors"].append(f"screen: {str(e)[:60]}")
    try:
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        snap["mouse"] = {"x": pt.x, "y": pt.y}
    except Exception as e:
        snap["errors"].append(f"mouse: {str(e)[:60]}")
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            snap["window"] = {"hwnd": hwnd, "title": buff.value}
    except Exception as e:
        snap["errors"].append(f"window: {str(e)[:60]}")
    return jsonify(snap)


@bp.route("/api/desktop/capabilities")
def api_desktop_capabilities():
    return jsonify({"ok": True, "capabilities": _DESKTOP_ACTIONS, "total": len(_DESKTOP_ACTIONS)})


@bp.route("/api/desktop/control-stack")
def api_desktop_control_stack():
    return jsonify(_sanitize_ui_payload(build_control_stack_report()))


@bp.route("/api/desktop/exec", methods=["POST"])
def api_desktop_exec():
    payload = request.json or {}
    cid = str(payload.get("id", "")).strip()
    if not cid:
        return jsonify({"ok": False, "error": "缺少桌面能力ID"}), 400
    allowed = {item["id"] for item in _DESKTOP_ACTIONS}
    if cid not in allowed:
        return jsonify({"ok": False, "error": "桌面能力不存在或已下线"}), 404
    try:
        if cid == "system_status":
            result = _exec_system_status()
        else:
            result = _exec_desktop(cid, payload)
        return jsonify(_sanitize_ui_payload(result))
    except Exception as e:
        return jsonify({"ok": False, "error": f"桌面执行失败: {str(e)[:120]}", "time": time.strftime("%H:%M:%S")}), 500


# ── 镜像空间插件（已装上，源自 paysssk-creator/jingxiangduoweidukongjian） ──
