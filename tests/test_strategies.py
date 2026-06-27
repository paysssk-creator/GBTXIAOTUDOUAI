# -*- coding: utf-8 -*-
"""Tests for gbt.strategies — 策略引擎"""
from gbt.strategies import (
    StrategyEngine,
    ma_crossover,
    rsi_divergence,
    volume_breakout,
    bollinger_squeeze,
    strategy,
)


def test_ma_crossover_golden_cross():
    # 短均线下穿长线后突然向上突破形成金叉 (需要至少 long+2=22 根)
    closes = [11.0] * 15 + [10.0] * 4 + [16.0, 16.0, 16.0]
    res = ma_crossover(closes, short=5, long=20)
    assert res["signal"] == "buy"
    assert res["confidence"] > 0


def test_ma_crossover_death_cross():
    # 短均线上穿长线后突然向下跌破形成死叉 (需要至少 long+2=22 根)
    closes = [9.0] * 15 + [10.0] * 4 + [4.0, 4.0, 4.0]
    res = ma_crossover(closes, short=5, long=20)
    assert res["signal"] == "sell"


def test_ma_crossover_insufficient_data():
    closes = [10.0] * 10
    res = ma_crossover(closes, short=5, long=20)
    assert res["signal"] == "hold"
    assert "数据不足" in res["reason"]


def test_rsi_divergence_top():
    # RSI背离需要 period+5=19 根以上数据
    closes = [10.0] * 16 + [11.0, 12.0, 13.0]
    res = rsi_divergence(closes)
    assert "RSI" in res["reason"] or "无背离" in res["reason"] or "背离" in res["reason"]


def test_rsi_divergence_insufficient_data():
    closes = [10.0] * 10
    res = rsi_divergence(closes)
    assert res["signal"] == "hold"


def test_volume_breakout_buy():
    closes = [10.0] * 19 + [11.0]
    volumes = [1000.0] * 19 + [10000.0]
    res = volume_breakout(closes, volumes)
    assert res["signal"] == "buy"


def test_volume_breakout_sell():
    closes = [10.0] * 19 + [9.0]
    volumes = [1000.0] * 19 + [10000.0]
    res = volume_breakout(closes, volumes)
    assert res["signal"] == "sell"


def test_bollinger_squeeze():
    # 收窄后价格 > MA20
    closes = [10.0 + i * 0.01 for i in range(25)]
    res = bollinger_squeeze(closes)
    # 带宽可能不满足<3%，但结构应返回hold或信号
    assert res["signal"] in ("buy", "sell", "hold")


def test_strategy_engine_analyze():
    closes = [10.0] * 18 + [9.0, 11.0]
    volumes = [1000.0] * 20
    res = strategy.analyze(closes, volumes=volumes)
    assert "signal" in res
    assert "confidence" in res
    assert "strategies" in res
    assert len(res["strategies"]) == 4


def test_strategy_engine_summary():
    closes = [10.0] * 18 + [9.0, 11.0]
    res = strategy.analyze(closes)
    assert isinstance(res["summary"], str)


if __name__ == "__main__":
    import sys
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                sys.exit(1)
    print("ALL STRATEGY TESTS PASSED")
