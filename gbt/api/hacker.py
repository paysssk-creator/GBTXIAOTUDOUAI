"""GBT Pro · gbt/api/hacker.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：hacker
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("hacker", __name__)


def _removed_response():
    return jsonify({
        "ok": False,
        "removed": True,
        "error": "黑客模块已下线，当前版本仅保留电脑操控与自主操盘能力"
    }), 410


@bp.route("/api/hacker/exec",methods=["POST"])
def hacker_exec_cap():
    """黑客模块已下线"""
    return _removed_response()

# ── 多策略引擎 API ──

@bp.route("/api/hacker/capabilities")
def hacker_all_caps():
    """黑客模块已下线"""
    return _removed_response()

