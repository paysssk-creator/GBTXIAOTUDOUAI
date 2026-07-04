"""GBT Pro · gbt/api/strategy.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：strategy
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("strategy", __name__)


@bp.route("/api/strategies")
def api_strategies():
    from gbt.multi_strategy import get_mse
    mse = get_mse()
    return jsonify({"strategies": [s.name for s in mse.strategies],
                   "history": mse.get_history(10),
                   "latest": [{"strategy": s.strategy, "signal": s.signal,
                               "confidence": s.confidence} for s in mse.latest()]})


@bp.route("/api/strategies/run/<code>")
def api_strategy_run(code):
    try:
        from gbt.live_market import get_market
        from gbt.multi_strategy import get_mse
        mkt = get_market()
        quote = mkt.get_quote(code) or {"code": code, "name": "未知", "price": 10}
        kl = mkt.get_daily_kline(code, 60)
        mse = get_mse()
        result = mse.run_all(kl, quote)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:100]})

# ── 审计日志 API ──
