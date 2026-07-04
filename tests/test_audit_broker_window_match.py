"""audit 窗口匹配纯函数测试"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gbt.api import audit


def test_enumerate_window_titles_keeps_all_unique_titles(monkeypatch):
    class FakeWin:
        def __init__(self, title):
            self.title = title

    fake_pyautogui = types.SimpleNamespace(
        getAllWindows=lambda: [
            FakeWin("WeChat"),
            FakeWin(""),
            FakeWin("网上股票交易系统 - 委托下单"),
            FakeWin("WeChat"),
            FakeWin("信e投交易客户端"),
        ]
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    assert audit._enumerate_window_titles() == [
        "WeChat",
        "网上股票交易系统 - 委托下单",
        "信e投交易客户端",
    ]


def test_match_broker_window_title_uses_ui_profile_keywords():
    hit = audit._match_broker_window_title("网上股票交易系统 - 委托下单")
    assert hit is not None
    assert hit["broker"] == "同花顺"
    assert any(word in (hit.get("matched_keywords") or []) for word in ["网上股票交易系统", "委托下单"])


def test_match_broker_window_title_matches_citic_alias():
    hit = audit._match_broker_window_title("信e投交易客户端")
    assert hit is not None
    assert hit["broker"] == "中信证券"
    assert any(word in (hit.get("matched_keywords") or []) for word in ["信e投", "交易客户端"])


def test_match_broker_window_title_matches_gbt_shell_alias_for_ths():
    hit = audit._match_broker_window_title("‎GBT全能小土豆CC – (2515202)")
    assert hit is not None
    assert hit["broker"] == "同花顺"
    assert any(word in (hit.get("matched_keywords") or []) for word in ["GBT全能小土豆CC", "GBT全能小土豆"])


def test_match_broker_window_title_returns_none_for_irrelevant_window():
    assert audit._match_broker_window_title("WeChat") is None

def test_trade_page_targets_include_profile_keywords():
    targets = audit._trade_page_targets(broker="同花顺", trade_action="buy", preferred_page="entrust")
    assert "买入" in targets
    assert any(word in targets for word in ["今日委托", "委托查询", "持仓查询"])



def test_trade_takeover_precheck_supports_app_only_mode():
    result = audit._trade_takeover_precheck(
        broker="同花顺",
        stock_code="600519",
        trade_action="buy",
        price=1420.55,
        lots=100,
        app_only=True,
    )

    assert result["app_only"] is True
    assert result["takeover_phase"] == "app_only"
    assert result["precheck_passed"] is True
    assert result["can_fill_form"] is True
    assert result["next_action_id"] == "trade_form_fill"
    assert result["supported_actions"] == ["trade_form_fill", "trade_submit_confirm", "trade_result_watch"]
    assert result["risk_gate"]["confirm_required_actions"] == ["trade_submit_confirm"]


def test_trade_takeover_precheck_hides_fill_warnings_before_ready(monkeypatch):
    monkeypatch.setattr(audit, "_trade_takeover_snapshot", lambda **kwargs: {
        "ok": True,
        "ready": False,
        "broker": "同花顺",
        "next_step": "请先打开并停留在真实券商交易客户端，AI 再继续接管。",
        "anchor_state": {"anchors": {}},
        "human_action_required": True,
    })
    monkeypatch.setattr(audit, "_detect_trade_confirm_dialog", lambda **kwargs: {
        "ok": True,
        "found": False,
        "confirm_btn": None,
        "keywords": [],
        "error": None,
    })

    result = audit._trade_takeover_precheck(broker="同花顺", trade_action="buy")

    assert result["precheck_passed"] is False
    assert result["next_action_id"] == "trade_takeover_watch"
    assert result["warnings"] == ["请先打开并停留在真实券商交易客户端，AI 再继续接管。"]
    assert result["missing_payload"] == ["stock_code", "price", "lots"]
    assert result["missing_fill_anchors"] == ["stock_code", "price", "lots"]


def test_trade_takeover_precheck_surfaces_fill_warnings_after_ready(monkeypatch):
    monkeypatch.setattr(audit, "_trade_takeover_snapshot", lambda **kwargs: {
        "ok": True,
        "ready": True,
        "broker": "同花顺",
        "next_step": "",
        "anchor_state": {"anchors": {"stock_code": True}},
        "human_action_required": False,
    })
    monkeypatch.setattr(audit, "_detect_trade_confirm_dialog", lambda **kwargs: {
        "ok": True,
        "found": False,
        "confirm_btn": None,
        "keywords": [],
        "error": None,
    })

    result = audit._trade_takeover_precheck(broker="同花顺", trade_action="buy")

    assert result["precheck_passed"] is True
    assert result["next_action_id"] == "trade_panel_probe"
    assert "缺少填单参数：stock_code, price, lots" in result["warnings"]
    assert "填单锚点未就绪：price, lots" in result["warnings"]
