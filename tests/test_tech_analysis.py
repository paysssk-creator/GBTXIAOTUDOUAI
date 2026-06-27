# -*- coding: utf-8 -*-
"""Tests for gbt.tech_analysis — 技术分析引擎"""
from gbt.tech_analysis import (
    SMA,
    EMA,
    MACD,
    RSI,
    BollingerBands,
    VolumeAnalysis,
    KDJ,
    FullAnalysis,
)


def test_sma_basic():
    assert SMA([1, 2, 3, 4, 5], 5) == 3.0


def test_sma_insufficient():
    assert SMA([1, 2, 3], 5) is None


def test_ema_basic():
    val = EMA([1, 2, 3, 4, 5], 5)
    assert val is not None
    assert val > 0


def test_rsi_overbought():
    closes = [10.0 + i * 0.5 for i in range(20)]
    res = RSI(closes)
    assert res["rsi"] is not None
    assert res["rsi"] >= 60


def test_rsi_oversold():
    closes = [20.0 - i * 0.5 for i in range(20)]
    res = RSI(closes)
    assert res["rsi"] is not None
    assert res["rsi"] <= 40


def test_macd_trend():
    closes = [10.0] * 40 + [11.0] * 10
    res = MACD(closes)
    assert "trend" in res
    assert res["macd"] is not None


def test_bollinger_bands():
    closes = [10.0 + (i % 5) * 0.1 for i in range(25)]
    res = BollingerBands(closes)
    assert res["upper"] is not None
    assert res["middle"] is not None
    assert res["lower"] is not None
    assert res["upper"] > res["middle"] > res["lower"]


def test_volume_analysis():
    volumes = [1000.0] * 19 + [6000.0]
    closes = [10.0] * 19 + [11.0]
    res = VolumeAnalysis(volumes, closes)
    assert res["ratio"] > 1.5
    assert "放量" in res["trend"]


def test_kdj_basic():
    highs = [i + 10 for i in range(20)]
    lows = [i + 5 for i in range(20)]
    closes = [i + 8 for i in range(20)]
    res = KDJ(highs, lows, closes)
    assert res["k"] is not None
    assert res["d"] is not None
    assert res["j"] is not None


def test_full_analysis_signal():
    closes = [10.0] * 18 + [9.0, 11.0]
    volumes = [1000.0] * 20
    highs = [10.2] * 18 + [9.5, 11.5]
    lows = [9.8] * 18 + [8.5, 10.5]
    res = FullAnalysis(closes, highs, lows, volumes, name="测试", code="sh000001")
    assert "signal" in res
    assert "indicators" in res
    assert res["signal"]["direction"] in ("buy", "sell", "hold")


def test_full_analysis_insufficient_data():
    res = FullAnalysis([1, 2, 3], name="测试", code="sh000001")
    assert "error" in res


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
    print("ALL TECH ANALYSIS TESTS PASSED")
