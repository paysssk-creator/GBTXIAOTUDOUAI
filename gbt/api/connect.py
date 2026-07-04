"""GBT Pro · gbt/api/connect.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：connect
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("connect", __name__)


@bp.route("/api/providers")
def prov():
    from gbt.providers import AutoKeyConfig;discovered=AutoKeyConfig.scan();result={}
    for pid,info in discovered.items():result[pid]={"name":info["config"]["name"],"status":info["status"]}
    return jsonify(result)

# ── GBT Brand: SVG Logo ──

@bp.route("/api/logo")
def api_logo():
    import os as _os
    fp = _os.path.join(_os.path.dirname(__file__), "desktop", "templates", "logo.svg")
    if _os.path.exists(fp):
        svg = open(fp, "r", encoding="utf-8").read()
    else:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="url(#g)"/><text x="32" y="43" text-anchor="middle" font-weight="900" font-size="34" fill="#fff">G</text></svg>'
    from flask import Response
    return Response(svg, mimetype="image/svg+xml",
                   headers={"Cache-Control": "public, max-age=86400"})


@bp.route("/api/devices")
def api_devices():return jsonify({"devices":[],"total":0})

@bp.route("/api/watcher/status")
def api_watcher_status():return jsonify({"running":False})

@bp.route("/api/trader/status")
def api_trader_status():return jsonify({"auto_trade":False})

@bp.route("/api/connectors")
def api_connectors():return jsonify({"connectors":[],"total":0})
# ── A股模拟交易账户 API ──
