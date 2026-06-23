"""
技术分析引擎 — RSI, MACD, 均线, 布林带, 量能分析
"""
import math
from collections import deque
from datetime import datetime
import logging

L = logging.getLogger("GBT.TechAnalysis")


def SMA(values, period):
    """简单移动平均"""
    if len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 2)


def EMA(values, period):
    """指数移动平均"""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return round(ema, 2)


def MACD(closes, fast=12, slow=26, signal=9):
    """MACD — 快慢均线差值和信号线"""
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "histogram": None, "trend": "数据不足"}

    ema_fast = EMA(closes, fast)
    ema_slow = EMA(closes, slow)
    if ema_fast is None or ema_slow is None:
        return {"macd": None, "signal": None, "histogram": None, "trend": "数据不足"}

    macd_val = round(ema_fast - ema_slow, 2)

    # 历史MACD值计算信号线
    macd_hist = []
    for i in range(slow, len(closes) - signal + 1):
        ef = EMA(closes[:i+1], fast)
        es = EMA(closes[:i+1], slow)
        if ef and es:
            macd_hist.append(ef - es)

    if len(macd_hist) < signal:
        signal_val = macd_val  # fallback
    else:
        signal_val = round(EMA(macd_hist, signal), 2)

    histogram = round(macd_val - signal_val, 2)
    
    if histogram > 0 and macd_hist and len(macd_hist) >= 2 and macd_hist[-2] < 0:
        trend = "🟢 金叉(看涨)"
    elif histogram < 0 and macd_hist and len(macd_hist) >= 2 and macd_hist[-2] > 0:
        trend = "🔴 死叉(看跌)"
    elif histogram > 0:
        trend = "🟡 多头"
    elif histogram < 0:
        trend = "🟡 空头"
    else:
        trend = "⚪ 持平"

    return {"macd": macd_val, "signal": signal_val, "histogram": histogram, "trend": trend}


def RSI(closes, period=14):
    """RSI 相对强弱指标"""
    if len(closes) < period + 1:
        return {"rsi": None, "zone": "数据不足"}

    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        rsi_val = 100
    else:
        rs = avg_gain / avg_loss
        rsi_val = round(100 - (100 / (1 + rs)), 1)

    if rsi_val >= 80:
        zone = "🔴 超买(≥80)"
    elif rsi_val >= 60:
        zone = "🟡 偏强(60-80)"
    elif rsi_val >= 40:
        zone = "⚪ 中性(40-60)"
    elif rsi_val >= 20:
        zone = "🟡 偏弱(20-40)"
    else:
        zone = "🟢 超卖(≤20)"

    return {"rsi": rsi_val, "zone": zone}


def BollingerBands(closes, period=20, std_dev=2):
    """布林带"""
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None, "width_pct": 0}

    middle = SMA(closes, period)
    if middle is None:
        return {"upper": None, "middle": None, "lower": None, "width_pct": 0}

    subset = closes[-period:]
    variance = sum((x - middle) ** 2 for x in subset) / period
    std = math.sqrt(variance)

    upper = round(middle + std_dev * std, 2)
    lower = round(middle - std_dev * std, 2)
    width_pct = round((upper - lower) / middle * 100, 1) if middle > 0 else 0

    last_price = closes[-1] if closes else 0
    if last_price >= upper:
        position = "触及上轨(超买)"
    elif last_price <= lower:
        position = "触及下轨(超卖)"
    elif last_price > middle:
        position = "中轨上方"
    else:
        position = "中轨下方"

    return {"upper": upper, "middle": middle, "lower": lower,
            "width_pct": width_pct, "position": position}


def VolumeAnalysis(volumes, closes):
    """量能分析"""
    if len(volumes) < 5 or len(closes) < 5:
        return {"trend": "数据不足", "ratio": 0, "climax": False}

    v5 = volumes[-5:]
    avg5 = sum(v5) / len(v5)
    v20 = sum(volumes[-20:]) / len(volumes[-20:]) if len(volumes) >= 20 else avg5
    
    ratio = round(avg5 / v20, 2) if v20 > 0 else 1

    if ratio > 2.0:
        trend = "🔥 放量巨量(>2倍)"
    elif ratio > 1.5:
        trend = "📊 温和放量(1.5-2倍)"
    elif ratio > 0.7:
        trend = "⚪ 正常量能"
    elif ratio > 0.4:
        trend = "📉 缩量(0.4-0.7倍)"
    else:
        trend = "❄️ 地量(<0.4倍)"

    # 量价配合
    price_up = closes[-1] > closes[-5] if len(closes) >= 5 else False
    if ratio > 1.5 and price_up:
        trend += " 量价齐升✅"
    elif ratio > 1.5 and not price_up:
        trend += " 放量下跌⚠️"
    elif ratio < 0.7 and not price_up:
        trend += " 缩量下跌"
    elif ratio < 0.7 and price_up:
        trend += " 缩量上涨⚠️"

    # 天量检测
    climax_all = max(volumes) if volumes else 0
    climax_avg = sum(volumes) / len(volumes) if volumes else 0
    climax = volumes[-1] > climax_avg * 2.5 if volumes else False

    return {"trend": trend, "ratio": ratio, "climax": climax}


def KDJ(highs, lows, closes, period=9):
    """KDJ随机指标"""
    if len(closes) < period:
        return {"k": None, "d": None, "j": None, "signal": "数据不足"}

    subset_highs = highs[-period:]
    subset_lows = lows[-period:]
    h = max(subset_highs)
    l = min(subset_lows)
    last_close = closes[-1]

    if h == l:
        rsv = 50
    else:
        rsv = (last_close - l) / (h - l) * 100

    # 简化KDJ (用历史均值)
    k = round(2/3 * 50 + 1/3 * rsv, 1)  # 简化计算
    d = round(2/3 * 50 + 1/3 * k, 1)
    j = round(3 * k - 2 * d, 1)

    if j > 100:
        signal = "🔴 超买(J>100)"
    elif j < 0:
        signal = "🟢 超卖(J<0)"
    elif k > d:
        signal = "🟡 K上穿D(金叉)"
    elif k < d:
        signal = "🟡 K下穿D(死叉)"
    else:
        signal = "⚪ 中性"

    return {"k": k, "d": d, "j": j, "signal": signal}


def FullAnalysis(close_prices, high_prices=None, low_prices=None, volumes=None,
                 name="未知", code=""):
    """完整技术分析报告"""
    if not close_prices or len(close_prices) < 20:
        return {"error": "历史数据不足(需≥20根K线)", "name": name, "code": code}

    if volumes is None:
        volumes = [0] * len(close_prices)
    if high_prices is None:
        high_prices = close_prices
    if low_prices is None:
        low_prices = close_prices

    current = close_prices[-1]

    rsi = RSI(close_prices)
    macd = MACD(close_prices)
    bb = BollingerBands(close_prices)
    vol = VolumeAnalysis(volumes, close_prices)
    kdj = KDJ(high_prices, low_prices, close_prices)

    ma5 = SMA(close_prices, 5)
    ma10 = SMA(close_prices, 10)
    ma20 = SMA(close_prices, 20)
    ma60 = SMA(close_prices, 60) if len(close_prices) >= 60 else None

    # 趋势判断
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            trend_desc = "📈 多头排列(强势上升)"
        elif ma5 < ma10 < ma20:
            trend_desc = "📉 空头排列(弱势下行)"
        elif ma5 > ma20 and current > ma20:
            trend_desc = "🟡 短多长(看涨)"
        else:
            trend_desc = "🟡 震荡整理"
    else:
        trend_desc = "数据不足"

    # 综合信号
    buy_signals = 0
    sell_signals = 0

    if rsi.get("rsi") and rsi["rsi"] < 30:
        buy_signals += 2
    elif rsi.get("rsi") and rsi["rsi"] > 70:
        sell_signals += 2

    if macd.get("histogram") and macd["histogram"] > 0:
        buy_signals += 1
    elif macd.get("histogram") and macd["histogram"] < 0:
        sell_signals += 1

    if "金叉" in macd.get("trend", ""):
        buy_signals += 2
    elif "死叉" in macd.get("trend", ""):
        sell_signals += 2

    if vol.get("climax"):
        sell_signals += 1  # 天量谨慎

    if bb.get("position") == "触及下轨(超卖)":
        buy_signals += 2
    elif bb.get("position") == "触及上轨(超买)":
        sell_signals += 2

    if kdj.get("signal") and "金叉" in kdj["signal"]:
        buy_signals += 1
    elif kdj.get("signal") and "死叉" in kdj["signal"]:
        sell_signals += 1

    confidence = round(abs(buy_signals - sell_signals) / 10 * 100, 1)
    if buy_signals > sell_signals:
        direction = "buy"
        confidence = min(95, confidence + 40)
    elif sell_signals > buy_signals:
        direction = "sell"
        confidence = min(95, confidence + 40)
    else:
        direction = "hold"
        confidence = 20

    return {
        "name": name,
        "code": code,
        "price": current,
        "indicators": {
            "rsi": rsi,
            "macd": macd,
            "bollinger": bb,
            "volume": vol,
            "kdj": kdj,
            "ma": {"ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60}
        },
        "trend": trend_desc,
        "signal": {
            "direction": direction,
            "confidence": confidence,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals
        }
    }
