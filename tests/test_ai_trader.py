# -*- coding: utf-8 -*-
"""Tests for gbt.gcc.ai_trader — AI 操盘手与 A 股规则集成"""
import sys
from unittest.mock import MagicMock

from gbt.gcc.ai_trader import AITrader, TradeDecision


def make_llm(responses):
    """按顺序返回预设回复的 mock LLM"""
    calls = {"i": 0}

    def invoke(msgs):
        idx = calls["i"]
        calls["i"] = idx + 1
        return responses[idx % len(responses)]

    return MagicMock(invoke=invoke)


def test_ai_trader_init():
    t = AITrader()
    assert t.llm is None
    assert t.desk is None


def test_analyze_screen_parses_json():
    raw = '{"app":"东方财富","view":"K线","code":"sh600519","price":1700.0}'
    t = AITrader(llm=make_llm([raw]))
    res = t.analyze_screen("fake_b64")
    assert res.get("app") == "东方财富"
    assert res.get("code") == "sh600519"


def test_analyze_screen_fallback_raw():
    t = AITrader(llm=make_llm(["这看起来是交易软件"]))
    res = t.analyze_screen("fake_b64")
    assert "raw" in res


def test_decide_parses_trade_decision():
    raw = '{"action":"buy","code":"sh600519","price":1700.0,"volume":100,"confidence":0.85}'
    t = AITrader(llm=make_llm([raw]))
    dec = t.decide({"code": "sh600519"})
    assert dec.action == "buy"
    assert dec.code == "sh600519"
    assert dec.volume == 100
    assert dec.confidence == 0.85


def test_decide_fallback_on_bad_json():
    t = AITrader(llm=make_llm(["没有JSON"]))
    dec = t.decide({})
    assert dec.action == "hold"


def test_observe_parses_json():
    raw = '{"app":"东方财富","is_trading":true,"done":false,"need_switch":false}'
    t = AITrader(llm=make_llm([raw]))
    res = t.observe("fake_b64")
    assert res["is_trading"] is True
    assert res["need_switch"] is False


def test_execute_trade_hold_returns_early():
    desk = MagicMock()
    t = AITrader(desk=desk)
    res = t.execute_trade(TradeDecision(action="hold"))
    assert res["ok"] is True
    desk.assert_not_called()


def test_execute_trade_buy_flow():
    desk = MagicMock()
    t = AITrader(desk=desk)
    dec = TradeDecision(action="buy", code="sh600519", price=1700.0, volume=100)
    res = t.execute_trade(dec, b64_before="fake")
    assert res["ok"] is True
    assert res["action"] == "buy"
    # 应输入代码、按 F1、输入价格、Tab、输入数量
    desk.keyboard_type.assert_any_call("sh600519")
    desk.keyboard_hotkey.assert_any_call(["f1"])
    desk.keyboard_type.assert_any_call("1700.0")
    desk.keyboard_type.assert_any_call("100")


def test_execute_trade_sell_flow():
    desk = MagicMock()
    t = AITrader(desk=desk)
    dec = TradeDecision(action="sell", code="sh600519", price=1700.0, volume=100)
    res = t.execute_trade(dec, b64_before="fake")
    assert res["ok"] is True
    desk.keyboard_hotkey.assert_any_call(["f2"])


def test_execute_trade_deduplicates_same_decision():
    desk = MagicMock()
    t = AITrader(desk=desk)
    dec = TradeDecision(action="buy", code="sh600519", price=1700.0, volume=100)
    t.execute_trade(dec, b64_before="fake")
    res = t.execute_trade(dec, b64_before="fake")
    assert res["action"] == "hold"
    # 第一次调用输入代码、价格、数量共 3 次 keyboard_type；第二次去重不执行
    assert desk.keyboard_type.call_count == 3


def test_execute_trade_normalizes_lot():
    desk = MagicMock()
    t = AITrader(desk=desk)
    # 150 股应被规整为 100 股
    dec = TradeDecision(action="buy", code="sh600519", price=1700.0, volume=150)
    res = t.execute_trade(dec, b64_before="fake")
    assert res["ok"] is True
    # 最终输入的数量应为 100 股
    calls = [call.args[0] for call in desk.keyboard_type.call_args_list]
    assert "100" in calls


def test_execute_trade_rejects_zero_lot():
    desk = MagicMock()
    t = AITrader(desk=desk)
    dec = TradeDecision(action="buy", code="sh600519", price=1700.0, volume=50)
    res = t.execute_trade(dec, b64_before="fake")
    assert res["ok"] is False
    assert "100股" in res["error"]


def test_reflect_parses_json():
    raw = '{"filled":true,"reason":"已成交"}'
    t = AITrader(llm=make_llm([raw]))
    res = t.reflect("b64b", "b64a", TradeDecision(action="buy"))
    assert res["filled"] is True


def test_run_hold_breaks_loop():
    t = AITrader(llm=make_llm([
        '{"app":"东方财富","is_trading":true}',
        '{"app":"东方财富","view":"K线","code":"sh600519"}',
        '{"action":"hold","code":"sh600519","price":1700.0,"volume":100,"confidence":0.5}'
    ]))
    t.capture = MagicMock(return_value="fake_b64")
    res = t.run("观望", max_attempts=1)
    assert res["ok"] is False  # hold 不视为成交
    assert res["attempts"] == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                sys.exit(1)
    print("ALL AI TRADER TESTS PASSED")
