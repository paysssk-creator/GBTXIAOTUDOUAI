"""GBT Pro · gbt/api/market.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：market
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("market", __name__)


@bp.route("/api/market")
def market():
    try:
        from gbt.connectors.market import get_indices as _gi
        return jsonify(_gi())
    except: return jsonify({"ok":False,"error":"Market not available"})


@bp.route("/api/market/stock/<code>")
def market_stock(code):
    code = code.strip()[:6]
    try:
        from gbt.connectors.market import get_stock as _gs
        return jsonify(_gs(code))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:120]})


@bp.route("/api/market/stock/<code>/history")
def market_stock_history(code):
    """单股行情 + 历史 K 线 + 技术指标摘要 — 专业终端一屏展示"""
    code = code.strip()[:6]
    period = (request.args.get("period", "daily") or "daily").strip()
    try:
        days = int(request.args.get("days", 60) or 60)
    except Exception as _e:
        return jsonify({"ok": False, "error": f"days 参数解析失败：{_e}"[:160]}), 400
    days = max(20, min(180, days))
    try:
        from gbt.connectors.market import get_stock as _gs
        from gbt.live_market import get_market
        quote = _gs(code)
        if not quote.get("ok"):
            return jsonify({"ok": False, "error": quote.get("error", "获取个股行情失败")})
        mkt = get_market()
        klines = mkt.get_daily_kline(code, days)
        summary = _tech_summary(klines)
        return jsonify({
            "ok": True,
            "code": code,
            "period": period,
            "quote": quote,
            "klines": klines[-60:],
            "summary": summary,
            "count": len(klines),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:160]})

def _tech_summary(klines):
    """纯 Python 计算 MA/MACD/KDJ/RSI — 不引第三方依赖"""
    closes = [float(k.get("close", 0)) for k in klines]
    highs = [float(k.get("high", 0)) for k in klines]
    lows = [float(k.get("low", 0)) for k in klines]
    vols = [float(k.get("volume", 0)) for k in klines]
    n = len(closes)
    if n < 5:
        return {"ok": False, "error": "K线数据不足"}

    # 逐日 MA 序列 — 用于前端 K 线 SVG 叠加
    def ma_seq(arr, p):
        out = []
        win = []
        for v in arr:
            win.append(v)
            if len(win) > p:
                win.pop(0)
            out.append(round(sum(win) / len(win), 3) if win else None)
        return out

    ma5_seq = ma_seq(closes, 5)
    ma10_seq = ma_seq(closes, 10)
    ma20_seq = ma_seq(closes, 20)

    def ma(arr, p):
        if len(arr) < p:
            return None
        return round(sum(arr[-p:]) / p, 3)

    ma5 = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)
    ma60 = ma(closes, 60) if n >= 60 else None
    last = closes[-1]
    prev = closes[-2] if n >= 2 else last

    # 均线形态
    pattern = "震荡"
    if ma5 and ma10 and ma20:
        if last > ma5 > ma10 > ma20:
            pattern = "多头排列"
        elif last < ma5 < ma10 < ma20:
            pattern = "空头排列"
        elif ma5 > ma10 and ma10 > ma20:
            pattern = "多头收敛"
        elif ma5 < ma10 and ma10 < ma20:
            pattern = "空头发散"

    # RSI(14) — Wilder 简化版
    rsi = None
    rsi_zone = "未知"
    if n >= 15:
        gains, losses = [], []
        for i in range(-14, 0):
            d = closes[i] - closes[i - 1]
            (gains if d > 0 else losses).append(abs(d))
        avg_g = sum(gains) / 14
        avg_l = sum(losses) / 14
        if avg_l == 0:
            rsi = 100.0
        else:
            rs = avg_g / avg_l
            rsi = round(100 - 100 / (1 + rs), 2)
        if rsi >= 80:
            rsi_zone = "严重超买"
        elif rsi >= 70:
            rsi_zone = "超买"
        elif rsi <= 20:
            rsi_zone = "严重超卖"
        elif rsi <= 30:
            rsi_zone = "超卖"
        else:
            rsi_zone = "中性"

    # MACD(12,26,9)
    macd = {"dif": None, "dea": None, "bar": None, "signal": "未知"}
    if n >= 26:
        ema12 = closes[0]
        ema26 = closes[0]
        difs = []
        for c in closes:
            ema12 = ema12 * (11 / 13) + c * (2 / 13)
            ema26 = ema26 * (25 / 27) + c * (2 / 27)
            difs.append(ema12 - ema26)
        dea = difs[0]
        deas = []
        for d in difs:
            dea = dea * (8 / 10) + d * (2 / 10)
            deas.append(dea)
        dif = round(difs[-1], 4)
        dea_v = round(deas[-1], 4)
        bar = round((dif - dea_v) * 2, 4)
        prev_dif = difs[-2]
        prev_dea = deas[-2]
        cross = "金叉" if (prev_dif <= prev_dea and dif > dea_v) else ("死叉" if (prev_dif >= prev_dea and dif < dea_v) else "柱状延续")
        macd = {"dif": dif, "dea": dea_v, "bar": bar, "signal": cross}

    # 成交量摘要
    vol_ratio = None
    if len(vols) >= 6:
        avg5 = sum(vols[-6:-1]) / 5
        if avg5 > 0:
            vol_ratio = round(vols[-1] / avg5, 2)
    avg20_vol = round(sum(vols[-20:]) / min(20, n), 0) if vols else 0

    # 振幅区间(最近 20)
    amp20 = None
    if n >= 20:
        seg_h = max(highs[-20:])
        seg_l = min(lows[-20:])
        if seg_l > 0:
            amp20 = round((seg_h - seg_l) / seg_l * 100, 2)

    return {
        "ok": True,
        "price": last,
        "prev_close": prev,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "ma5_seq": ma5_seq, "ma10_seq": ma10_seq, "ma20_seq": ma20_seq,
        "ma_pattern": pattern,
        "rsi": rsi, "rsi_zone": rsi_zone,
        "macd": macd,
        "vol_ratio": vol_ratio,
        "avg_volume_20": avg20_vol,
        "amp20": amp20,
        "bias5": round((last - ma5) / ma5 * 100, 2) if ma5 else None,
        "bias10": round((last - ma10) / ma10 * 100, 2) if ma10 else None,
        "bias20": round((last - ma20) / ma20 * 100, 2) if ma20 else None,
        "support": round(min(lows[-20:]), 3) if n >= 20 else None,
        "resist": round(max(highs[-20:]), 3) if n >= 20 else None,
        "data_points": n,
    }

# ── 每日复盘解说 ──

@bp.route("/api/market/recap", methods=["POST", "GET"])
def market_recap():
    """每日复盘 — DeepSeek-reasoner 汇总指数/自选/策略状态生成盘后解读"""
    payload = request.json if request.method == "POST" else {}
    payload = payload if isinstance(payload, dict) else {}

    # 解析当前用户（与 chat 一致，支持登录会话绑定）
    user_id = "_default"
    user_token = ""
    try:
        token = payload.get("token", "") or request.headers.get("X-Auth-Token", "")
        if token:
            from gbt.auth import get_auth, get_balance
            verified = get_auth().verify_session(token)
            if verified:
                user_id = verified
                user_token = token
                bal = get_balance().get_balance(user_id)
                remaining = max(0, int(bal.get("tokens", 0)) - int(bal.get("used", 0)))
                if remaining < 200:
                    return jsonify({"ok": False, "error": "Token 余额不足 200T，每日复盘需要专业推理模型"}), 402
            else:
                return jsonify({"ok": False, "error": "会话过期，请重新登录"}), 401
    except Exception:
        pass

    # 收集市场结构化数据
    snap = {"indices": [], "watchlist": [], "pilot": None, "kline_window": {}}
    try:
        from gbt.connectors.market import get_indices as _gi
        ind = _gi()
        items = ind.get("indices") if isinstance(ind, dict) else None
        if not items and isinstance(ind, dict):
            items = ind.get("data", {}).get("diff") if isinstance(ind.get("data"), dict) else ind.get("data")
        if isinstance(items, list) and items:
            snap["indices"] = [
                {"name": i.get("name"), "price": i.get("price"), "pct": i.get("pct"), "change": i.get("change")}
                for i in items[:8]
            ]
    except Exception:
        pass

    try:
        from gbt.live_market import get_market
        mkt = get_market()
        from gbt import live_market as _lm
        wl_quotes = []
        # 优先使用本地仪表盘自选，若没有则按当前活跃关注列表
        try:
            from gbt.connectors.market import market_handle as _mh
            wl_handle = _mh("get_watchlist") if False else None
        except Exception:
            wl_handle = None
        # 兜底：使用 autopilot 多策略默认观察名单
        try:
            from gbt.multi_strategy import get_strategy_engine
            eng = get_strategy_engine()
            watch = []
            for s in getattr(eng, "strategies", []):
                sym = getattr(s, "symbols", None) or []
                watch.extend(sym[:6])
            seen = set(); codes = []
            for c in watch:
                c = str(c).strip()
                if re.fullmatch(r"\d{6}", c) and c not in seen:
                    seen.add(c); codes.append(c)
            for code in codes[:6]:
                q = mkt.get_quote(code)
                if q:
                    wl_quotes.append({
                        "code": code,
                        "name": (q.get("name") if isinstance(q, dict) else ""),
                        "price": q.get("price") if isinstance(q, dict) else None,
                        "pct": q.get("pct") if isinstance(q, dict) else None,
                    })
        except Exception:
            pass
        snap["watchlist"] = wl_quotes
    except Exception:
        pass

    try:
        from gbt.autopilot import get_autopilot
        ap = get_autopilot()
        if ap:
            status = ap.status()
            snap["pilot"] = {
                "running": status.get("running"),
                "scan_count": status.get("scan_count"),
                "last_scan": status.get("last_scan_time"),
                "strategy": status.get("current_strategy") or status.get("strategy"),
                "positions": status.get("position_count") or len(status.get("positions", [])),
            }
    except Exception:
        pass

    # 让 LLM 不接触实时动态查询 — 我们固定给出"系统当前可见"的快照
    import json as _json
    snap_text = _json.dumps(snap, ensure_ascii=False)

    system_prompt = (
        "你是一位拥有 10 年 A 股交易经验的职业操盘手，"
        "现在正在给机构客户写盘后每日复盘报告。要求：\n"
        "1) 只能基于【系统实时给出的市场快照】数字，禁止编造任何未在快照中出现的代码/数字。\n"
        "2) 语气专业、克制，可以给出方向性判断，但要明确风险。\n"
        "3) 输出必须严格按以下 4 段，用中文输出，每段 80–160 字：\n"
        "   【今日主基调】\n"
        "   【资金与风格】\n"
        "   【强者与机会】\n"
        "   【明日盯盘点】\n"
        "4) 不要使用 markdown 标题，不要使用编号列表。"
    )
    user_prompt = (
        f"【系统实时市场快照 / {payload.get('today', '今日')} / "
        f"GBT Pro 终端】\n{snap_text}\n\n"
        "请按要求输出 4 段中文复盘。"
    )

    # 强制走 deepseek-reasoner，确保专业度
    content = ""
    reasoning = ""
    provider = "deepseek"
    model_name = "deepseek-reasoner"
    used_metrics = {"tokens_in": 0, "tokens_out": 0}
    try:
        import os
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_KEY", "")
        from gbt.llm import GBTLLM
        llm = GBTLLM(provider="deepseek", model="deepseek-reasoner",
                     api_key=api_key, temperature=0.3, max_tokens=2400, timeout=120)
        model_name = llm.model
        provider = llm.provider
        content = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]) or ""
        used_metrics["tokens_in"] = max(1, len(user_prompt) // 3)
        used_metrics["tokens_out"] = max(1, len(content) // 3)
    except Exception as e:
        return jsonify({"ok": False, "error": "复盘生成失败：" + str(e)[:160]}), 500

    # Token 扣费
    consumed = used_metrics["tokens_in"] + used_metrics["tokens_out"]
    consumed = max(consumed, 200)  # 设 200 T 为最低门槛，避免低价白嫖
    try:
        from gbt.auth import get_balance
        get_balance().consume(user_id, consumed)
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "today": payload.get("today"),
        "headline": _recap_summary_line(content),
        "report": content,
        "model": model_name,
        "provider": provider,
        "snap": snap,
        "tokens_consumed": consumed,
        "user": user_id,
    })


def _recap_summary_line(text):
    """从复盘文本中提取一句话标题"""
    if not text:
        return "今日市场复盘"
    for line in text.splitlines():
        s = line.strip().lstrip("# ").strip()
        if s.startswith("【今日主基调】"):
            t = s.replace("【今日主基调】", "", 1).strip()
            return ("今日主基调：" + t)[:120] if t else "今日主基调已生成"
    return text.strip().splitlines()[0][:120] if text.strip() else "今日市场复盘"

# ── LLM 连接 API ──

@bp.route("/api/stock/<code>")
def api_stock_lookup(code):
    """个股实时行情查询"""
    code = code.strip()[:6]
    try:
        from gbt.capabilities import _handler_stock_lookup
        result = _handler_stock_lookup(code)
        return jsonify({
            "ok": True,
            "code": code,
            "quote": str(result)[:2000]
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:100]})

