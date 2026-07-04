"""
multi_strategy.py — 多策略并行引擎 + A/B对比
支持: MA组合/RSI反转/MACD金叉/布林突破/AI自主
"""
import time, json, logging, threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

L = logging.getLogger("gbt.strategies")


@dataclass
class StratSignal:
    strategy: str
    code: str
    name: str
    signal: str  # BUY/SELL/HOLD
    confidence: float = 0.0
    price: float = 0
    reasoning: str = ""
    timestamp: str = ""


class BaseStrategy:
    """策略基类"""
    name = "base"
    description = ""

    def analyze(self, klines: List[Dict], quote: Dict) -> StratSignal:
        raise NotImplementedError


class MAStrategy(BaseStrategy):
    """MA均线组合策略 (5/20/60)"""
    name = "ma_combo"
    description = "MA5/MA20/MA60多空排列"

    def analyze(self, klines, quote):
        code = quote.get("code", "")
        name = quote.get("name", "")
        price = quote.get("price", 0)
        closes = [k["close"] for k in klines[-60:]] if len(klines) >= 60 else [k["close"] for k in klines]
        if len(closes) < 20:
            return StratSignal(self.name, code, name, "HOLD", 0, price, "K线不足")
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes) / len(closes) if len(closes) >= 60 else ma20
        if price > ma5 > ma20 > ma60:
            return StratSignal(self.name, code, name, "BUY", 0.7, price,
                              f"多头排列 MA5={ma5:.1f}>{ma20:.1f}>{ma60:.1f}")
        elif price < ma5 < ma20:
            return StratSignal(self.name, code, name, "SELL", 0.6, price,
                              f"空头排列 MA5={ma5:.1f}<{ma20:.1f}<{ma60:.1f}")
        return StratSignal(self.name, code, name, "HOLD", 0.3, price, "均线缠绕")


class RSIStrategy(BaseStrategy):
    """RSI超买超卖策略"""
    name = "rsi_reversal"
    description = "RSI超卖买入/超买卖出"

    def analyze(self, klines, quote):
        code = quote.get("code", "")
        name = quote.get("name", "")
        price = quote.get("price", 0)
        closes = [k["close"] for k in klines[-20:]]
        if len(closes) < 15:
            return StratSignal(self.name, code, name, "HOLD", 0, price, "数据不足")
        gains = [max(0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        losses = [max(0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
        avg_gain = sum(gains) / max(len(gains), 1)
        avg_loss = sum(losses) / max(len(losses), 1)
        rsi = 50 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
        if rsi < 25:
            return StratSignal(self.name, code, name, "BUY", 0.75, price, f"RSI超卖={rsi:.0f}")
        elif rsi > 75:
            return StratSignal(self.name, code, name, "SELL", 0.7, price, f"RSI超买={rsi:.0f}")
        return StratSignal(self.name, code, name, "HOLD", max(0.3, abs(rsi - 50) / 50), price,
                          f"RSI中性={rsi:.0f}")


class MACDStrategy(BaseStrategy):
    """MACD金叉死叉策略"""
    name = "macd_cross"
    description = "MACD金叉买入/死叉卖出"

    def analyze(self, klines, quote):
        code = quote.get("code", "")
        name = quote.get("name", "")
        price = quote.get("price", 0)
        closes = [k["close"] for k in klines[-40:]]
        if len(closes) < 27:
            return StratSignal(self.name, code, name, "HOLD", 0, price, "数据不足")
        ema12 = closes[0]
        ema26 = closes[0]
        difs = []
        for c in closes:
            ema12 = ema12 * 11 / 13 + c * 2 / 13
            ema26 = ema26 * 25 / 27 + c * 2 / 27
            difs.append(ema12 - ema26)
        if len(difs) < 10:
            return StratSignal(self.name, code, name, "HOLD", 0, price)
        dea9 = sum(difs[-9:]) / 9
        dif_now = difs[-1]
        dif_prev = difs[-2] if len(difs) > 1 else dif_now
        if dif_prev < dea9 and dif_now > dea9:
            return StratSignal(self.name, code, name, "BUY", 0.7, price, "MACD金叉")
        elif dif_prev > dea9 and dif_now < dea9:
            return StratSignal(self.name, code, name, "SELL", 0.65, price, "MACD死叉")
        return StratSignal(self.name, code, name, "HOLD", 0.2, price, "MACD无信号")


class BollingerStrategy(BaseStrategy):
    """布林带突破策略"""
    name = "bollinger_break"
    description = "下轨买入/上轨卖出"

    def analyze(self, klines, quote):
        code = quote.get("code", "")
        name = quote.get("name", "")
        price = quote.get("price", 0)
        closes = [k["close"] for k in klines[-20:]]
        if len(closes) < 20:
            return StratSignal(self.name, code, name, "HOLD", 0, price)
        ma20 = sum(closes) / len(closes)
        std = (sum((c - ma20) ** 2 for c in closes) / len(closes)) ** 0.5
        upper = ma20 + 2 * std
        lower = ma20 - 2 * std
        if price <= lower:
            return StratSignal(self.name, code, name, "BUY", 0.65, price,
                              f"跌破下轨 MA20={ma20:.1f} Lower={lower:.1f}")
        elif price >= upper:
            return StratSignal(self.name, code, name, "SELL", 0.6, price,
                              f"突破上轨 MA20={ma20:.1f} Upper={upper:.1f}")
        return StratSignal(self.name, code, name, "HOLD", 0.2, price, "布林带内")


class MultiStrategyEngine:
    """多策略并行 + 投票决策"""

    def __init__(self):
        self.strategies = [
            MAStrategy(), RSIStrategy(), MACDStrategy(), BollingerStrategy()
        ]
        self.results_lock = threading.Lock()
        self.latest_results = []
        self.history = []

    def run_all(self, klines: List[Dict], quote: Dict) -> Dict:
        """并行运行所有策略 → 投票"""
        signals = []
        for strat in self.strategies:
            sig = strat.analyze(klines, quote)
            signals.append(sig)

        # 投票
        buy_votes = sum(1 for s in signals if s.signal == "BUY")
        sell_votes = sum(1 for s in signals if s.signal == "SELL")
        total = len(signals)
        buy_conf = buy_votes / total
        sell_conf = sell_votes / total

        final_signal = "HOLD"
        if buy_votes >= 3:
            final_signal = "BUY"
        elif sell_votes >= 3:
            final_signal = "SELL"

        result = {
            "code": quote.get("code", ""),
            "name": quote.get("name", ""),
            "price": quote.get("price", 0),
            "signal": final_signal,
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
            "hold_votes": total - buy_votes - sell_votes,
            "signal_detail": [{"strategy": s.strategy, "signal": s.signal,
                               "confidence": s.confidence, "reasoning": s.reasoning} for s in signals],
            "timestamp": time.strftime("%H:%M:%S"),
        }

        with self.results_lock:
            self.latest_results = signals
            self.history.append(result)
            if len(self.history) > 200:
                self.history = self.history[-200:]

        return result

    def latest(self):
        return self.latest_results

    def get_history(self, limit=20):
        return self.history[-limit:]


# 全局单例
_mse = None


def get_mse() -> MultiStrategyEngine:
    global _mse
    if _mse is None:
        _mse = MultiStrategyEngine()
    return _mse
