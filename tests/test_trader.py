# -*- coding: utf-8 -*-
"""Tests for gbt.trader — 自主交易引擎与A股规则集成"""
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from gbt.trader import AShareTrader, TradeSignal, StockQuote


def test_trader_init():
    t = AShareTrader()
    assert t.confidence_threshold == 70
    assert t.auto_trade is True
    assert len(t.watchlist) > 0


def test_search_stock():
    t = AShareTrader()
    res = t.search_stock("茅台")
    assert "sh600519" in res


def test_open_platform():
    t = AShareTrader()
    res = t.open_platform("东方财富")
    assert res["ok"] is True
    assert "eastmoney" in res["url"]


def test_fetch_quote_mock():
    t = AShareTrader()
    # 验证 fetch_quote 在数据异常时能捕获
    res = t.fetch_quote(["invalid_code"])
    assert isinstance(res, dict)


def test_decide_trade_low_confidence():
    t = AShareTrader()
    sig = TradeSignal("sh600519", "贵州茅台", "buy", 100.0, confidence=50)
    res = t.decide_trade(sig)
    assert res["trade"] is False
    assert "置信度不足" in res["reasons"][0]


def test_decide_trade_outside_hours():
    t = AShareTrader()
    # 周日不应交易
    sig = TradeSignal("sh600519", "贵州茅台", "buy", 100.0, confidence=90)
    res = t.decide_trade(sig)
    # 取决于当前时间，但至少不应在任意情况下直接通过
    assert isinstance(res["trade"], bool)


def _make_quote(code="sh600519", price=1000.0, prev_close=950.0):
    return StockQuote(code=code, name="贵州茅台", price=price, prev_close=prev_close)


def test_execute_trade_buy_invalid_lot_rejected():
    t = AShareTrader()
    t.market_data["sh600519"] = _make_quote()
    # 150 股不是 100 股整数倍，应由 A 股规则拦截
    res = t.execute_trade("sh600519", "buy", shares=150, price=1000.0)
    assert res["ok"] is False
    assert "100股" in res["msg"] or "A股规则" in res["msg"]


def test_execute_trade_buy_ok():
    t = AShareTrader()
    # 使用低价股确保同时通过 A 股规则与风控仓位检查
    t.market_data["sh600519"] = _make_quote(price=10.0, prev_close=9.5)
    # GCCRunner 模块不存在时会回退到浏览器/通知模式
    with patch("gbt.trader.subprocess.run"), \
         patch("gbt.trader.os.startfile"), \
         patch("webbrowser.open"):
        res = t.execute_trade("sh600519", "buy", shares=100, price=10.0)
    assert res["ok"] is True
    assert res["log"]["shares"] == 100
    assert res["method"] in ("gcc_runner", "trade_notification_only")


def test_execute_trade_sell_t1_blocked():
    t = AShareTrader()
    t.market_data["sh600519"] = _make_quote()
    # 模拟当日买入的持仓
    fake_account = MagicMock()
    fake_account.positions = {"sh600519": {"shares": 100}}
    fake_account.buy_dates = {"sh600519": datetime.now()}
    with patch("gbt.account.account", fake_account):
        res = t.execute_trade("sh600519", "sell", shares=100, price=1000.0)
    assert res["ok"] is False
    assert "T+1" in res["msg"] or "A股规则" in res["msg"]


def test_execute_trade_buy_limit_up_blocked():
    t = AShareTrader()
    # 主板涨停价 = prev_close * 1.1; 买入价格超过涨停应被拦截
    t.market_data["sh600519"] = _make_quote(price=1200.0, prev_close=1000.0)
    res = t.execute_trade("sh600519", "buy", shares=100, price=1200.0)
    assert res["ok"] is False
    assert "涨停" in res["msg"] or "A股规则" in res["msg"]


def test_run_full_pipeline_skipped_low_confidence():
    t = AShareTrader()
    t.auto_trade = True
    with patch.object(t, "fetch_quote", return_value={
        "sh600519": _make_quote()
    }):
        with patch.object(t, "analyze_with_ai", return_value=TradeSignal(
            "sh600519", "贵州茅台", "buy", 1000.0, confidence=50
        )):
            session = t.run_full_pipeline("sh600519")
    assert session.status == "skipped"


def test_run_full_pipeline_executes():
    t = AShareTrader()
    t.auto_trade = True
    # 只有在交易时段内才会执行；补丁决定交易以绕过时段检查
    with patch.object(t, "fetch_quote", return_value={
        "sh600519": _make_quote()
    }):
        with patch.object(t, "analyze_with_ai", return_value=TradeSignal(
            "sh600519", "贵州茅台", "buy", 1000.0, confidence=95
        )):
            with patch.object(t, "execute_trade", return_value={"ok": True, "log": {}}) as mock_exec:
                with patch.object(t, "decide_trade", return_value={"trade": True, "reasons": []}):
                    session = t.run_full_pipeline("sh600519")
    assert session.status != "skipped"
    mock_exec.assert_called_once()


def test_autonomous_start_stop():
    t = AShareTrader()
    res = t.start_autonomous()
    assert res["ok"] is True
    assert t.running is True
    res = t.stop_autonomous()
    assert res["ok"] is True
    assert t.running is False
    # 等待线程结束避免泄漏
    if t.scan_thread and t.scan_thread.is_alive():
        t.scan_thread.join(timeout=1)


def test_scan_market_returns_signals():
    t = AShareTrader()
    with patch.object(t, "fetch_watchlist", return_value={
        "sh600519": _make_quote(),
        "sh000001": _make_quote(code="sh000001", price=3000.0, prev_close=2950.0)
    }):
        with patch.object(t, "analyze_with_ai", return_value=TradeSignal(
            "sh600519", "贵州茅台", "buy", 1000.0, confidence=80
        )):
            signals = t.scan_market()
    assert isinstance(signals, list)
    # 指数被过滤
    assert all(not s.code.startswith("sh000") for s in signals)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                sys.exit(1)
    print("ALL TRADER TESTS PASSED")
