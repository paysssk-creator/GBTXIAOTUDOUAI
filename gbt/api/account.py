"""GBT Pro · gbt/api/account.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：account
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
from gbt.api.llm import _resolve_token_user
bp = Blueprint("account", __name__)


def _recharge_removed_response():
    return jsonify({
        "ok": False,
        "removed": True,
        "error": "付费模块已下线，充值入口不可用。当前版本仅保留电脑操控与自主操盘主能力。"
    }), 410


@bp.route("/api/account")
def api_account():
    """完整账户状态 — 持仓明细 + 成交记录"""
    try:
        from gbt.paper_account import get_state, get_trades
        state = get_state()
        trades = get_trades(30)
        return jsonify({
            "ok": True,
            "cash": state["cash"],
            "equity": state["equity"],
            "pnl": state["total_pnl"],
            "positions": list(state["positions"].values()),
            "position_count": len(state["positions"]),
            "trades": trades,
            "created": state.get("created", ""),
            "updated": state.get("updated", ""),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:100]})


@bp.route("/api/account/trades")
def api_account_trades():
    """成交记录 — 每条可查询"""
    try:
        from gbt.paper_account import get_trades
        return jsonify({"ok": True, "trades": get_trades(100)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:100]})


@bp.route("/api/account/positions")
def api_account_positions():
    """持仓明细 — 每只可查"""
    try:
        from gbt.paper_account import get_state
        state = get_state()
        return jsonify({"ok": True, "positions": list(state["positions"].values()),
                       "cash": state["cash"], "equity": state["equity"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:100]})


@bp.route("/api/account/reset")
def api_account_reset():
    """重置模拟账户"""
    from gbt.paper_account import reset
    return jsonify(reset())


@bp.route("/api/account/order", methods=["POST"])
def api_account_order():
    """模拟下单"""
    d = request.json or {}
    code = d.get("code", "").strip()
    name = d.get("name", code)
    side = d.get("side", "BUY")
    price = float(d.get("price", 10))
    shares = int(d.get("shares", 100))
    from gbt.paper_account import place_order
    return jsonify(place_order(code, name, side, price, shares))


@bp.route("/api/token/balance")
def token_balance():
    """查询 Token 余额 — T-008 修复：直接读真实余额，无 10000 fake fallback

    Response shape（兼容前端 layout.html:790 与 healthcheck.py）：
      {"ok": True, "tokens": int, "used": int, "remaining": int, "plan": str}
    任何异常一律 500（不再静默返回 fake 10000）
    """
    try:
        user, auth_error = _resolve_token_user({})
        if auth_error:
            return auth_error
        from gbt.auth import get_balance
        bal = get_balance().get_balance(user)
        tokens = int(bal.get("tokens", 0))
        used = int(bal.get("used", 0))
        remaining = max(0, tokens - used)
        plan = str(bal.get("plan", "none"))
        return jsonify({
            "ok": True,
            "tokens": tokens,
            "used": used,
            "remaining": remaining,
            "plan": plan,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"余额查询失败：{e}"}), 500


@bp.route("/api/token/recharge", methods=["POST"])
def token_recharge():
    return _recharge_removed_response()


@bp.route("/api/token/plans")
def token_plans():
    try:
        from gbt.auth import get_balance
        return jsonify({"ok": True, "plans": get_balance().plans()})
    except Exception:
        return jsonify({"ok": True, "plans": []})

# ── 用户认证 API ──
