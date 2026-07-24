"""
策略引擎 — 多策略并行分析, 综合打分
"""
import logging

L = logging.getLogger("GBT.Strategy")


def ma_crossover(closes, short=5, long=20):
    """
    均线交叉策略
    返回: {signal: buy/sell/hold, confidence: 0-100, reason: str}
    """
    if len(closes) < long + 2:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}

    # 计算均线
    def ma(vals, n):
        return sum(vals[-n:]) / n

    ma_s = ma(closes, short)
    ma_l = ma(closes, long)
    ma_s_prev = ma(closes[:-1], short)
    ma_l_prev = ma(closes[:-1], long)

    spread_pct = round(abs(ma_s - ma_l) / ma_l * 100, 2)
    price = closes[-1]

    # 金叉：短线从下穿上长线
    if ma_s_prev <= ma_l_prev and ma_s > ma_l:
        conf = min(85, 50 + spread_pct * 5)
        return {"signal": "buy", "confidence": round(conf, 1),
                "reason": f"📈 金叉 MA{short}({ma_s:.1f}) ↑ MA{long}({ma_l:.1f}) · 乖离{spread_pct}%"}

    # 死叉：短线从上穿下长线
    if ma_s_prev >= ma_l_prev and ma_s < ma_l:
        conf = min(85, 50 + spread_pct * 5)
        return {"signal": "sell", "confidence": round(conf, 1),
                "reason": f"📉 死叉 MA{short}({ma_s:.1f}) ↓ MA{long}({ma_l:.1f}) · 乖离{spread_pct}%"}

    # 多头排列
    if ma_s > ma_l and price > ma_s:
        conf = min(75, 40 + spread_pct * 3)
        return {"signal": "buy", "confidence": round(conf, 1),
                "reason": f"📊 多头排列 MA{short}({ma_s:.1f}) > MA{long}({ma_l:.1f})"}

    # 空头排列
    if ma_s < ma_l and price < ma_s:
        conf = min(75, 40 + spread_pct * 3)
        return {"signal": "sell", "confidence": round(conf, 1),
                "reason": f"📊 空头排列 MA{short}({ma_s:.1f}) < MA{long}({ma_l:.1f})"}

    return {"signal": "hold", "confidence": 10,
            "reason": f"均线整理 MA{short}={ma_s:.1f} MA{long}={ma_l:.1f}"}


def rsi_divergence(closes, high_prices=None, period=14):
    """
    RSI 背离策略
    价格创新高/低，但RSI未确认 → 反转信号
    """
    if len(closes) < period + 5:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}

    if high_prices is None:
        high_prices = closes

    # 简化RSI计算
    def calc_rsi(vals):
        gains, losses = [], []
        for i in range(1, len(vals)):
            d = vals[i] - vals[i-1]
            gains.append(max(d, 0))
            losses.append(max(-d, 0))
        avg_g = sum(gains[-period:]) / period
        avg_l = sum(losses[-period:]) / period
        if avg_l == 0:
            return 100
        return round(100 - 100 / (1 + avg_g / avg_l), 1)

    rsi_now = calc_rsi(closes)
    rsi_prev = calc_rsi(closes[:-3])

    price_now = closes[-1]
    price_prev_high = max(closes[-8:-2])

    # 顶背离：价格创新高，RSI未创新高
    if price_now > price_prev_high and rsi_now < rsi_prev:
        return {"signal": "sell", "confidence": 65,
                "reason": f"🔻 RSI顶背离 价{price_now:.2f}↑ RSI{rsi_now}↓"}

    # 底背离：价格创新低，RSI未创新低
    price_prev_low = min(closes[-8:-2])
    if price_now < price_prev_low and rsi_now > rsi_prev:
        return {"signal": "buy", "confidence": 65,
                "reason": f"🔺 RSI底背离 价{price_now:.2f}↓ RSI{rsi_now}↑"}

    return {"signal": "hold", "confidence": 0,
            "reason": f"无背离 RSI={rsi_now}"}


def volume_breakout(closes, volumes, vol_multiple=2.0, price_threshold=0.02):
    """
    放量突破策略
    成交量突然放大 + 价格突破关键位
    """
    if len(closes) < 20 or len(volumes) < 20:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}

    avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    latest_vol = volumes[-1]
    latest_price = closes[-1]
    prev_close = closes[-2]

    vol_ratio = round(latest_vol / avg_vol, 2) if avg_vol > 0 else 1
    price_change = round((latest_price - prev_close) / prev_close * 100, 2)

    # 计算20日最高价
    high20 = max(closes[-20:])
    low20 = min(closes[-20:])

    # 放量突破上方
    if vol_ratio >= vol_multiple and latest_price >= high20 * (1 - price_threshold):
        conf = min(80, 45 + vol_ratio * 10)
        return {"signal": "buy", "confidence": round(conf, 1),
                "reason": f"🔥 放量突破 量比{vol_ratio}x · 涨{price_change}% · 突破20日高{high20:.2f}"}

    # 放量跌破下方
    if vol_ratio >= vol_multiple and latest_price <= low20 * (1 + price_threshold):
        conf = min(80, 45 + vol_ratio * 10)
        return {"signal": "sell", "confidence": round(conf, 1),
                "reason": f"💥 放量下破 量比{vol_ratio}x · 跌{abs(price_change)}% · 跌破20日低{low20:.2f}"}

    return {"signal": "hold", "confidence": 10,
            "reason": f"量比{vol_ratio}x · 常态"}


def bollinger_squeeze(closes, period=20, std=2):
    """
    布林带收窄 → 即将变盘
    """
    if len(closes) < period + 5:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}

    def bb_width(vals):
        ma = sum(vals[-period:]) / period
        variance = sum((x - ma) ** 2 for x in vals[-period:]) / period
        std_val = variance ** 0.5
        return (std_val * 2 * std) / ma * 100  # 带宽百分比

    width_now = bb_width(closes)
    width_prev = bb_width(closes[:-5])

    if width_now < 3 and width_prev > width_now:
        # 带宽<3% 且收窄 → squeeze
        price_ma20 = sum(closes[-20:]) / 20
        if closes[-1] > price_ma20:
            return {"signal": "buy", "confidence": 55,
                    "reason": f"🔄 布林收窄突破 带宽{width_now:.1f}% · 价>均线"}
        else:
            return {"signal": "sell", "confidence": 55,
                    "reason": f"🔄 布林收窄下破 带宽{width_now:.1f}% · 价<均线"}

    return {"signal": "hold", "confidence": 0, "reason": f"布林带宽{width_now:.1f}%"}



# ═══════════ GBT v5.0 专业级策略扩展 ═══════════

def support_resistance(highs, lows, closes, lookback=20):
    """支撑阻力位分析 — 基于近期高低点和成交量密集区"""
    if len(closes) < lookback:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}
    
    recent_high = max(highs[-lookback:])
    recent_low = min(lows[-lookback:])
    current = closes[-1]
    price_range = recent_high - recent_low
    
    if price_range == 0:
        return {"signal": "hold", "confidence": 0, "reason": "价格不变"}
    
    # 计算距离支撑/阻力的百分比
    dist_to_resist = (recent_high - current) / price_range * 100
    dist_to_support = (current - recent_low) / price_range * 100
    
    # 靠近支撑位 + 有反弹迹象 = 买入信号
    if dist_to_support < 20 and closes[-1] > closes[-2]:
        conf = min(80, 50 + (20 - dist_to_support) * 2)
        return {"signal": "buy", "confidence": round(conf, 1),
                "reason": f"📐 接近支撑 {recent_low:.2f} (距离{dist_to_support:.0f}%) · 反弹确认"}
    
    # 靠近阻力位 + 有回落迹象 = 卖出信号
    if dist_to_resist < 20 and closes[-1] < closes[-2]:
        conf = min(80, 50 + (20 - dist_to_resist) * 2)
        return {"signal": "sell", "confidence": round(conf, 1),
                "reason": f"📐 接近阻力 {recent_high:.2f} (距离{dist_to_resist:.0f}%) · 遇阻回落"}
    
    # 突破阻力 = 强势买入
    if current > recent_high and closes[-2] <= recent_high:
        return {"signal": "buy", "confidence": 75,
                "reason": f"🚀 突破阻力 {recent_high:.2f} · 打开上涨空间"}
    
    # 跌破支撑 = 卖出
    if current < recent_low and closes[-2] >= recent_low:
        return {"signal": "sell", "confidence": 80,
                "reason": f"⚠️ 跌破支撑 {recent_low:.2f} · 止损信号"}
    
    return {"signal": "hold", "confidence": 15,
            "reason": f"支撑{recent_low:.2f} ← {current:.2f} → 阻力{recent_high:.2f}"}


def trend_strength(closes, period=14):
    """趋势强度分析 — ADX简化版 + 均线排列"""
    if len(closes) < period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}
    
    # 计算方向性移动 (+DM/-DM)
    up_moves = []
    down_moves = []
    true_ranges = []
    for i in range(1, len(closes)):
        up = closes[i] - closes[i-1] if closes[i] > closes[i-1] else 0
        down = closes[i-1] - closes[i] if closes[i] < closes[i-1] else 0
        up_moves.append(up)
        down_moves.append(down)
        true_ranges.append(abs(closes[i] - closes[i-1]))
    
    # 平滑
    def ema(data, n):
        k = 2 / (n + 1)
        result = [data[0]]
        for v in data[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result
    
    atr = ema(true_ranges, period)[-1]
    plus_di = ema(up_moves, period)[-1] / atr * 100 if atr > 0 else 0
    minus_di = ema(down_moves, period)[-1] / atr * 100 if atr > 0 else 0
    
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    
    if dx > 40 and plus_di > minus_di:
        return {"signal": "buy", "confidence": min(85, dx),
                "reason": f"📈 强趋势上涨 ADX~{dx:.0f} · +DI={plus_di:.0f} > -DI={minus_di:.0f}"}
    elif dx > 40 and minus_di > plus_di:
        return {"signal": "sell", "confidence": min(85, dx),
                "reason": f"📉 强趋势下跌 ADX~{dx:.0f} · -DI={minus_di:.0f} > +DI={plus_di:.0f}"}
    elif dx < 20:
        return {"signal": "hold", "confidence": 10,
                "reason": f"📊 无明显趋势 ADX~{dx:.0f} · 震荡市"}
    
    return {"signal": "hold", "confidence": 20,
            "reason": f"ADX~{dx:.0f} +DI={plus_di:.0f} -DI={minus_di:.0f}"}


def fibonacci_retracement(highs, lows, closes):
    """斐波那契回撤分析"""
    if len(closes) < 30:
        return {"signal": "hold", "confidence": 0, "reason": "数据不足"}
    
    swing_high = max(highs[-30:])
    swing_low = min(lows[-30:])
    current = closes[-1]
    price_range = swing_high - swing_low
    
    if price_range == 0:
        return {"signal": "hold", "confidence": 0, "reason": "无波动区间"}
    
    fib_levels = {
        "0.236": swing_high - price_range * 0.236,
        "0.382": swing_high - price_range * 0.382,
        "0.500": swing_high - price_range * 0.500,
        "0.618": swing_high - price_range * 0.618,
        "0.786": swing_high - price_range * 0.786,
    }
    
    # 找最近的关键斐波那契位
    nearest_level = None
    nearest_dist = float('inf')
    for level_name, level_price in fib_levels.items():
        dist = abs(current - level_price) / price_range * 100
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_level = (level_name, level_price)
    
    level_name, level_price = nearest_level
    
    # 回撤到0.618且止跌 = 黄金买点
    if level_name in ("0.618", "0.786") and current > closes[-2]:
        return {"signal": "buy", "confidence": 70,
                "reason": f"✨ 斐波那契{level_name}回撤 {level_price:.2f} · 黄金买点"}
    
    # 反弹到0.382且遇阻 = 卖点
    if level_name in ("0.236", "0.382") and current < closes[-2]:
        return {"signal": "sell", "confidence": 65,
                "reason": f"📐 斐波那契{level_name}反弹遇阻 {level_price:.2f}"}
    
    return {"signal": "hold", "confidence": 20,
            "reason": f"斐波那契 最近位:{level_name}({level_price:.2f}) 距离{nearest_dist:.1f}%"}

class StrategyEngine:
    """多策略综合评分引擎"""

    STRATEGIES = [
        ("MA交叉", ma_crossover),
        ("RSI背离", rsi_divergence),
        ("放量突破", volume_breakout),
        ("布林收窄", bollinger_squeeze),
        ("支撑阻力", support_resistance),
        ("趋势强度", trend_strength),
        ("斐波那契", fibonacci_retracement),
    ]

    def __init__(self):
        self.weights = {"MA交叉": 1.5, "RSI背离": 1.0, "放量突破": 1.2, "布林收窄": 0.8, "支撑阻力": 1.3, "趋势强度": 1.4, "斐波那契": 1.0}

    def analyze(self, closes, highs=None, lows=None, volumes=None):
        """
        综合多策略分析
        返回: {signal: buy/sell/hold, confidence: 0-100, strategies: [...], summary: str}
        """
        if highs is None:
            highs = closes
        if lows is None:
            lows = closes
        if volumes is None:
            volumes = [0] * len(closes)

        results = []
        total_buy = 0
        total_sell = 0

        for name, fn in self.STRATEGIES:
            try:
                if name == "RSI背离":
                    r = fn(closes, highs)
                elif name == "放量突破":
                    r = fn(closes, volumes)
                else:
                    r = fn(closes)
                r["strategy_name"] = name
                w = self.weights.get(name, 1.0)

                if r["signal"] == "buy":
                    total_buy += r.get("confidence", 0) * w
                elif r["signal"] == "sell":
                    total_sell += r.get("confidence", 0) * w

                results.append(r)
            except Exception as e:
                L.warning(f"策略 {name} 异常: {e}")
                results.append({"strategy_name": name, "signal": "hold",
                               "confidence": 0, "reason": f"异常: {e}"})

        # 综合
        net = total_buy - total_sell
        if net > 30:
            direction = "buy"
            confidence = round(min(95, net / 2), 1)
        elif net < -30:
            direction = "sell"
            confidence = round(min(95, abs(net) / 2), 1)
        else:
            direction = "hold"
            confidence = round(max(0, 50 - abs(net) / 2), 1)

        active = [r for r in results if r["signal"] != "hold"]
        summary = "; ".join(f"{r['strategy_name']}:{r.get('reason','')[:40]}" for r in active[:3]) or "无明确信号"

        return {
            "signal": direction,
            "confidence": confidence,
            "strategies": results,
            "buy_score": round(total_buy, 1),
            "sell_score": round(total_sell, 1),
            "summary": summary
        }


# 全局策略引擎
strategy = StrategyEngine()
