# -*- coding: utf-8 -*-
"""Tests for gbt.backtest — 回测引擎"""
from gbt.backtest import BacktestEngine


def build_kline(prices, volumes=None):
    volumes = volumes or [1000.0] * len(prices)
    raw = []
    for i, (p, v) in enumerate(zip(prices, volumes)):
        day = f"2026-01-{i + 1:02d}"
        raw.append({
            "day": day,
            "open": p - 0.1,
            "close": p,
            "high": p + 0.1,
            "low": p - 0.1,
            "volume": v,
        })
    return {
        "closes": prices,
        "highs": [p + 0.1 for p in prices],
        "lows": [p - 0.1 for p in prices],
        "volumes": volumes,
        "raw": raw,
    }


def strategy_always_buy(closes, highs, lows, volumes, idx):
    return {"signal": "buy", "confidence": 100, "reason": "always buy"}


def strategy_always_sell(closes, highs, lows, volumes, idx):
    return {"signal": "sell", "confidence": 100, "reason": "always sell"}


def test_backtest_insufficient_data():
    bt = BacktestEngine()
    kline = build_kline([10.0] * 10)
    res = bt.run("sh600519", kline, strategy_always_buy)
    assert res.final_equity == bt.initial_capital


def test_backtest_buy_and_hold():
    bt = BacktestEngine()
    prices = [10.0] * 25 + [12.0] * 5
    kline = build_kline(prices)
    res = bt.run("sh600519", kline, strategy_always_buy)
    assert res.total_trades >= 1
    assert res.final_equity > bt.initial_capital


def test_backtest_short_and_lose():
    bt = BacktestEngine()
    prices = [10.0] * 25 + [12.0] * 5
    kline = build_kline(prices)
    res = bt.run("sh600519", kline, strategy_always_sell)
    # 没有持仓情况下 always_sell 不会触发交易
    assert res.total_trades == 0


def test_backtest_stop_loss():
    bt = BacktestEngine()
    bt.stop_loss_pct = 5
    prices = [10.0] * 25 + [8.0] * 10
    kline = build_kline(prices)
    res = bt.run("sh600519", kline, strategy_always_buy)
    # 买入后触发止损
    assert res.total_trades >= 1


def test_backtest_metrics():
    bt = BacktestEngine()
    prices = list(range(20, 45))  # 持续上涨
    kline = build_kline(prices)
    res = bt.run("sh600519", kline, strategy_always_buy)
    assert res.total_return > 0
    assert res.max_drawdown >= 0
    assert res.win_rate >= 0
    assert res.profit_factor >= 0
    assert len(res.equity_curve) > 0


def test_run_with_gbt_strategies():
    bt = BacktestEngine()
    prices = [10.0] * 25 + [12.0] * 5
    kline = build_kline(prices)
    res = bt.run_with_gbt_strategies("sh600519", kline)
    assert res is not None
    assert hasattr(res, "total_return")


def test_parameter_scan():
    bt = BacktestEngine()
    prices = [10.0] * 25 + [12.0] * 5
    kline = build_kline(prices)
    grid = {"stop_loss_pct": [5, 7], "confidence_threshold": [50, 60]}
    res = bt.run_parameter_scan("sh600519", kline, grid, strategy_always_buy)
    assert res["total_combinations"] == 4
    assert "best_params" in res
    assert "top5" in res


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
    print("ALL BACKTEST TESTS PASSED")
