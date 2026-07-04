"""GBT Pro · gbt/api/panel.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：panel
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time, sys
from pathlib import Path
from gbt.release_meta import runtime_identity
bp = Blueprint("panel", __name__)


def _ui_safe_path(raw: str) -> str:
    path = Path(raw)
    try:
        base = Path.cwd().resolve() if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
        rel = path.resolve().relative_to(base)
        prefix = "[runtime]/" if getattr(sys, "frozen", False) else "[project]/"
        return prefix + str(rel).replace("\\", "/")
    except Exception:
        return path.name or "[path]"


@bp.route("/api/panel/status")
def api_panel_status():
    ident = runtime_identity()
    return jsonify({
        "ok": True,
        "role": ident["role"],
        "version": ident["version"],
        "release_tag": ident["release_tag"],
        "data_dir": _ui_safe_path(ident["data_dir"]),
        "log_dir": _ui_safe_path(ident["log_dir"]),
    })



@bp.route("/api/panel/rollback", methods=["POST"])
def api_panel_rollback():
    """面板回滚触发 — 仅当 deploy/atomic_switch.py 在容器外被允许时生效"""
    ident = runtime_identity()
    return jsonify({
        "ok": True,
        "action": "rollback",
        "note": "由部署面板 atomic_switch.py 自动接收；当前进程已暴露接口",
        "version": ident["version"],
    })

# ── 自主操盘引擎 API ──
