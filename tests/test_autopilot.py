# -*- coding: utf-8 -*-
"""Tests for gbt.autopilot — 桌面自主操盘引擎"""
import sys
from unittest.mock import MagicMock, patch

from gbt.autopilot import Autopilot, TradingAction, TradingSkills


def test_autopilot_init():
    ap = Autopilot()
    assert ap.turn_count == 0
    assert ap.MAX_TURNS == 30
    assert ap._stop is False


def test_trading_skills_dispatch():
    skills = TradingSkills()
    # 直接调用技能应返回动作描述，不依赖真实桌面
    with patch("gbt.autopilot.pyautogui.click") as mock_click:
        res = skills.skill_click(100, 200)
    assert res["ok"] is True
    mock_click.assert_called_once_with(100, 200, button="left")

    with patch("gbt.autopilot.pyautogui.write") as mock_write:
        res = skills.skill_type("hello", interval=0.01)
    assert res["ok"] is True
    mock_write.assert_called_once_with("hello", interval=0.01)


def test_mock_analyze_buy_task():
    ap = Autopilot()
    actions = ap._mock_analyze("买入 600519")
    types = [a.action_type for a in actions]
    assert "click" in types
    assert "type" in types
    assert "press" in types


def test_mock_analyze_sell_task():
    ap = Autopilot()
    actions = ap._mock_analyze("卖出 贵州茅台")
    types = [a.action_type for a in actions]
    assert "click" in types
    assert "type" in types


def test_mock_analyze_analysis_task():
    ap = Autopilot()
    actions = ap._mock_analyze("分析走势K线")
    types = [a.action_type for a in actions]
    assert "scroll" in types


def test_execute_dispatches_actions():
    ap = Autopilot()
    with patch.object(ap.skills, "skill_click", return_value={"ok": True}) as mock_click:
        res = ap.execute(TradingAction("click", params={"x": 100, "y": 200}))
    assert res["ok"] is True
    mock_click.assert_called_once_with(100, 200, "left")


def test_execute_unknown_action():
    ap = Autopilot()
    res = ap.execute(TradingAction("unknown", params={}))
    assert res["ok"] is True


def test_verify_returns_bool():
    ap = Autopilot()
    before = MagicMock()
    after = MagicMock()
    before.image.resize.return_value = MagicMock()
    after.image.resize.return_value = MagicMock()
    # numpy 在函数内导入，mock numpy.array 以拦截 ndarray 转换
    with patch("numpy.array", return_value=MagicMock(
        astype=lambda t: MagicMock(
            __sub__=lambda other: MagicMock(
                __abs__=MagicMock(return_value=MagicMock(mean=lambda: 0.05))
            )
        )
    )):
        res = ap.verify(before, after, TradingAction("click"))
    assert isinstance(res, bool)


def test_run_stops_at_max_turns():
    ap = Autopilot()
    fake_screen = MagicMock()
    fake_screen.base64 = "fake"
    with patch.object(ap, "capture", return_value=fake_screen):
        with patch.object(ap, "analyze", return_value=[TradingAction("wait", params={"seconds": 0.01})]):
            with patch.object(ap, "execute", return_value={"ok": True}):
                with patch("gbt.autopilot.time.sleep"):
                    res = ap.run("测试任务")
    assert res.ok is True
    assert res.actions_executed > 0
    assert ap.turn_count == ap.MAX_TURNS


def test_stop_flag():
    ap = Autopilot()
    ap.stop()
    assert ap._stop is True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                sys.exit(1)
    print("ALL AUTOPILOT TESTS PASSED")
