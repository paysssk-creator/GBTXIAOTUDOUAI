"""GBT Pro · gbt/api/pilot.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：pilot
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("pilot", __name__)


@bp.route("/api/pilot/start", methods=["GET", "POST"])
def api_pilot_start():
    from gbt.autopilot import get_pilot
    return jsonify(get_pilot().start())


@bp.route("/api/pilot/stop", methods=["GET", "POST"])
def api_pilot_stop():
    from gbt.autopilot import get_pilot
    return jsonify(get_pilot().stop())


@bp.route("/api/pilot/status")
def api_pilot_status():
    from gbt.autopilot import get_pilot
    return jsonify(get_pilot().status())


@bp.route("/api/pilot/config", methods=["POST"])
def api_pilot_config():
    from gbt.autopilot import get_pilot
    return jsonify(get_pilot().update_config(request.json or {}))


@bp.route("/api/pilot/signals")
def api_pilot_signals():
    from gbt.autopilot import get_pilot
    p = get_pilot()
    return jsonify({"signals": p.state.get("signals", []), "last_scan": p.state.get("last_scan")})
