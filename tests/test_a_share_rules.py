# -*- coding: utf-8 -*-
"""Tests for gbt.a_share_rules — A股专业知识可执行化验证"""
from datetime import datetime, timedelta

from gbt.a_share_rules import (
    MIN_COMMISSION,
    AShareRuleEngine,
    Board,
    a_share,
    board_name,
    get_rules_summary,
)


def test_detect_board_main():
    assert a_share.detect_board("sh600519", "贵州茅台") == Board.MAIN
    assert a_share.detect_board("sz000858", "五粮液") == Board.MAIN


def test_detect_board_star():
    assert a_share.detect_board("sh688981", "中芯国际") == Board.STAR


def test_detect_board_chinext():
    assert a_share.detect_board("sz300750", "宁德时代") == Board.CHINEXT


def test_detect_board_bse():
    assert a_share.detect_board("bj430047", "某北交所") == Board.BSE


def test_detect_board_st_by_name():
    assert a_share.detect_board("sh600000", "*ST某某") == Board.ST
    assert a_share.detect_board("sz000001", "ST平安") == Board.ST


def test_limit_prices_main():
    up, down = a_share.limit_prices("sh600519", 100.0)
    assert up == 110.0
    assert down == 90.0


def test_limit_prices_star():
    up, down = a_share.limit_prices("sh688981", 50.0)
    assert up == 60.0
    assert down == 40.0


def test_limit_prices_st():
    up, down = a_share.limit_prices("sh600000", 10.0, "*ST测试")
    assert up == 10.5
    assert down == 9.5


def test_price_in_limit():
    assert a_share.price_in_limit("sh600519", 105.0, 100.0) is True
    assert a_share.price_in_limit("sh600519", 120.0, 100.0) is False
    assert a_share.price_in_limit("sh600519", 80.0, 100.0) is False


def test_normalize_lot():
    assert a_share.normalize_lot(50) == 0
    assert a_share.normalize_lot(100) == 100
    assert a_share.normalize_lot(250) == 200
    assert a_share.normalize_lot(1000) == 1000


def test_validate_lot():
    ok, _ = a_share.validate_lot(100)
    assert ok
    ok, msg = a_share.validate_lot(150)
    assert not ok
    assert "100股" in msg
    ok, msg = a_share.validate_lot(0)
    assert not ok


def test_trading_time_weekday():
    monday_morning = datetime(2026, 6, 29, 10, 0)  # Monday
    assert a_share.is_trading_time(monday_morning) is True
    lunch = datetime(2026, 6, 29, 12, 0)
    assert a_share.is_trading_time(lunch) is False
    sunday = datetime(2026, 6, 28, 10, 0)  # Sunday
    assert a_share.is_trading_time(sunday) is False


def test_call_auction_time():
    auction = datetime(2026, 6, 29, 9, 20)
    assert a_share.is_call_auction_time(auction) is True
    continuous = datetime(2026, 6, 29, 9, 30)
    assert a_share.is_call_auction_time(continuous) is False


def test_t1_can_sell():
    buy = datetime(2026, 6, 29, 10, 0)
    same_day = datetime(2026, 6, 29, 14, 0)
    next_day = datetime(2026, 6, 30, 10, 0)
    assert a_share.can_sell_today(buy, same_day) is False
    assert a_share.can_sell_today(buy, next_day) is True


def test_calc_buy_fees():
    fees = a_share.calc_buy_fees(100000, "sh600519")
    assert fees["commission"] == 25.0
    assert fees["stamp_tax"] == 0.0
    assert fees["transfer_fee"] == 1.0
    assert fees["total"] == 26.0


def test_calc_sell_fees():
    fees = a_share.calc_sell_fees(100000, "sh600519")
    assert fees["commission"] == 25.0
    assert fees["stamp_tax"] == 50.0
    assert fees["transfer_fee"] == 1.0
    assert fees["total"] == 76.0


def test_shenzhen_no_transfer_fee():
    fees = a_share.calc_buy_fees(100000, "sz000858")
    assert fees["transfer_fee"] == 0.0


def test_min_commission():
    fees = a_share.calc_buy_fees(1000, "sh600519")
    assert fees["commission"] == MIN_COMMISSION


def test_check_buy_success():
    res = a_share.check_buy("sh600519", 100, 100.0, 100.0, 20000)
    assert res.ok is True
    assert res.adjusted_shares == 100
    assert res.fees["total"] > 0


def test_check_buy_lot_invalid():
    res = a_share.check_buy("sh600519", 150, 100.0, 100.0, 20000)
    assert res.ok is False
    assert res.adjusted_shares == 100


def test_check_buy_over_limit_up():
    res = a_share.check_buy("sh600519", 100, 120.0, 100.0, 20000)
    assert res.ok is False
    assert "涨跌停" in res.reason


def test_check_buy_insufficient_cash():
    res = a_share.check_buy("sh600519", 1000, 100.0, 100.0, 5000)
    assert res.ok is False
    assert "资金不足" in res.reason
    assert res.adjusted_shares == 0


def test_check_sell_success():
    buy_date = datetime.now() - timedelta(days=1)
    res = a_share.check_sell(
        "sh600519", 100, 105.0, 100.0, 500, buy_date=buy_date
    )
    assert res.ok is True


def test_check_sell_t1_blocked():
    buy_date = datetime.now()
    res = a_share.check_sell(
        "sh600519", 100, 105.0, 100.0, 500, buy_date=buy_date
    )
    assert res.ok is False
    assert "T+1" in res.reason


def test_check_sell_over_limit_down():
    buy_date = datetime.now() - timedelta(days=1)
    res = a_share.check_sell(
        "sh600519", 100, 80.0, 100.0, 500, buy_date=buy_date
    )
    assert res.ok is False
    assert "涨跌停" in res.reason


def test_board_name():
    assert board_name(Board.STAR) == "科创板"
    assert board_name(Board.CHINEXT) == "创业板"


def test_rules_summary():
    summary = get_rules_summary()
    assert "T+1" in summary
    assert "主板10%" in summary


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
    print("ALL A-SHARE RULE TESTS PASSED")
