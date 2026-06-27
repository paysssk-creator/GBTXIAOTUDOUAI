# -*- coding: utf-8 -*-
"""Tests for gbt.account — 账户追踪、持仓、盈亏"""
from datetime import datetime, timedelta

from gbt.account import Account


def test_initial_state():
    acc = Account(initial_cash=100000)
    pnl = acc.get_pnl()
    assert pnl["equity"] == 100000
    assert pnl["cash"] == 100000
    assert pnl["pnl"] == 0
    assert pnl["total_trades"] == 0


def test_buy_creates_position():
    acc = Account(initial_cash=100000)
    res = acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    assert res["ok"] is True
    assert acc.cash < 100000
    assert "sh600519" in acc.positions
    assert acc.positions["sh600519"]["shares"] == 100


def test_buy_insufficient_funds():
    acc = Account(initial_cash=10000)
    res = acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    assert res["ok"] is False
    assert "资金不足" in res["error"]


def test_sell_realizes_pnl():
    acc = Account(initial_cash=100000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    res = acc.sell("sh600519", 100, 1100.0)
    assert res["ok"] is True
    assert res["entry"]["pnl"] == 10000
    assert "sh600519" not in acc.positions
    assert acc.total_trades == 2


def test_sell_partial_position():
    acc = Account(initial_cash=100000)
    acc.buy("sh600519", "贵州茅台", 200, 400.0)
    res = acc.sell("sh600519", 100, 500.0)
    assert res["ok"] is True
    assert acc.positions["sh600519"]["shares"] == 100


def test_sell_without_position():
    acc = Account(initial_cash=100000)
    res = acc.sell("sh600519", 100, 1000.0)
    assert res["ok"] is False
    assert "无持仓" in res["error"]


def test_avg_cost_after_multiple_buys():
    acc = Account(initial_cash=250000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    acc.buy("sh600519", "贵州茅台", 100, 1200.0)
    pos = acc.positions["sh600519"]
    assert pos["avg_cost"] == 1100.0
    assert pos["shares"] == 200


def test_get_equity_with_market_prices():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    equity = acc.get_equity({"sh600519": 1200.0})
    # cash 100000 + 120000 = 220000
    assert equity == 220000


def test_get_positions_with_value():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    positions = acc.get_positions_with_value({"sh600519": 1100.0})
    assert positions["sh600519"]["value"] == 110000
    assert positions["sh600519"]["pnl"] == 10000
    assert positions["sh600519"]["pnl_pct"] == 10.0


def test_win_rate():
    acc = Account(initial_cash=300000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    acc.sell("sh600519", 100, 1100.0)  # win
    acc.buy("sh600000", "浦发银行", 100, 1000.0)
    acc.sell("sh600000", 100, 900.0)  # loss
    pnl = acc.get_pnl()
    # Account counts every buy/sell as a trade, so 4 total, 1 win, 1 loss
    assert pnl["win_rate"] == 25.0
    assert acc.win_trades == 1
    assert acc.loss_trades == 1


def test_config():
    acc = Account(initial_cash=100000)
    cfg = acc.get_config()
    assert cfg["initial_cash"] == 100000
    assert cfg["positions_count"] == 0


def test_buy_normalizes_lot():
    acc = Account(initial_cash=200000)
    res = acc.buy("sh600519", "贵州茅台", 150, 1000.0)
    assert res["ok"] is True
    assert acc.positions["sh600519"]["shares"] == 100


def test_sell_normalizes_lot():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 200, 500.0)
    res = acc.sell("sh600519", 150, 600.0)
    assert res["ok"] is True
    assert acc.positions["sh600519"]["shares"] == 100


def test_can_sell_t1_blocks_same_day():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    today = datetime.now()
    res = acc.can_sell("sh600519", 100, sell_date=today)
    assert res["ok"] is False
    assert "T+1" in res["reason"]


def test_can_sell_next_day_ok():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    tomorrow = datetime.now() + timedelta(days=1)
    res = acc.can_sell("sh600519", 100, sell_date=tomorrow)
    assert res["ok"] is True


def test_buy_records_date():
    acc = Account(initial_cash=200000)
    acc.buy("sh600519", "贵州茅台", 100, 1000.0)
    assert "sh600519" in acc.buy_dates
    assert isinstance(acc.buy_dates["sh600519"], datetime)


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
    print("ALL ACCOUNT TESTS PASSED")
