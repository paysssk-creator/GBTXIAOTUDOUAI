# -*- coding: utf-8 -*-
"""Tests for gbt.risk_ctrl — 风控引擎"""
from gbt.risk_ctrl import RiskManager


class FakeSignal:
    def __init__(self, code, action, price, confidence=80, reason=""):
        self.code = code
        self.action = action
        self.price = price
        self.confidence = confidence
        self.reason = reason


class FakePosition:
    def __init__(self, shares, avg_cost):
        self.shares = shares
        self.avg_cost = avg_cost


def test_position_size_basic():
    rm = RiskManager(total_capital=100000)
    res = rm.check_position_size(100.0)
    assert res["ok"] is True
    # 单票上限20% -> 20000 / 100 = 200股
    assert res["max_shares"] == 200


def test_position_size_invalid_price():
    rm = RiskManager(total_capital=100000)
    res = rm.check_position_size(0)
    assert res["ok"] is False
    assert "价格无效" in res["reason"]


def test_check_stop_loss_triggered():
    rm = RiskManager(total_capital=100000)
    res = rm.check_stop_loss("sh600519", 100.0, 92.0)
    assert res["triggered"] is True
    assert res["action"] == "sell"
    assert res["loss_pct"] == 8.0


def test_check_stop_loss_not_triggered():
    rm = RiskManager(total_capital=100000)
    res = rm.check_stop_loss("sh600519", 100.0, 95.0)
    assert res["triggered"] is False
    assert res["action"] == "hold"


def test_check_stop_profit_triggered():
    rm = RiskManager(total_capital=100000)
    res = rm.check_stop_profit("sh600519", 100.0, 116.0)
    assert res["triggered"] is True
    assert res["action"] == "sell"


def test_trailing_stop_triggered():
    rm = RiskManager(total_capital=100000)
    res = rm.check_stop_profit("sh600519", 100.0, 112.0, high_price=120.0)
    assert res["triggered"] is True
    # 回撤 (120-112)/120 = 6.67% >= 5%
    assert "移动止损" in res["reason"]


def test_daily_limit_initial():
    rm = RiskManager(total_capital=100000)
    daily = rm.check_daily_limit()
    assert daily["can_trade"] is True
    assert daily["trades_left"] == 10
    assert daily["loss_limit_hit"] is False


def test_daily_limit_trades_exhausted():
    rm = RiskManager(total_capital=100000)
    rm.daily_trades = 10
    daily = rm.check_daily_limit()
    assert daily["can_trade"] is False


def test_daily_limit_loss_hit():
    rm = RiskManager(total_capital=100000)
    rm.daily_pnl = -6000
    daily = rm.check_daily_limit()
    assert daily["loss_limit_hit"] is True
    assert daily["can_trade"] is False


def test_approve_trade_buy_ok():
    rm = RiskManager(total_capital=100000)
    sig = FakeSignal("sh600519", "buy", 100.0, confidence=80)
    res = rm.approve_trade(sig)
    assert res["approved"] is True
    assert res["action"] == "buy"


def test_approve_trade_sell_stop_loss_forced():
    rm = RiskManager(total_capital=100000)
    positions = {"sh600519": FakePosition(100, 100.0)}
    sig = FakeSignal("sh600519", "sell", 92.0, confidence=60)
    res = rm.approve_trade(sig, positions=positions)
    assert res["action"] == "sell"
    assert res["confidence"] == 100
    assert "[风控]" in sig.reason


def test_approve_trade_daily_limit_blocks():
    rm = RiskManager(total_capital=100000)
    rm.daily_trades = 10
    sig = FakeSignal("sh600519", "buy", 100.0, confidence=90)
    res = rm.approve_trade(sig)
    assert res["approved"] is False
    assert "交易次数" in res["issues"][0]


def test_record_trade():
    rm = RiskManager(total_capital=100000)
    rm.record_trade(pnl=1000)
    assert rm.daily_trades == 1
    assert rm.daily_pnl == 1000


def test_reset_daily():
    rm = RiskManager(total_capital=100000)
    rm.record_trade(pnl=-5000)
    rm.reset_daily()
    assert rm.daily_trades == 0
    assert rm.daily_pnl == 0


def test_get_status():
    rm = RiskManager(total_capital=100000)
    status = rm.get_status()
    assert status["total_capital"] == 100000
    assert status["stop_loss_pct"] == 7


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
    print("ALL RISK CONTROL TESTS PASSED")
