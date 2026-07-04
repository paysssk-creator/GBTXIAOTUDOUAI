"""tests/test_api_strategy.py · T-003 · strategy blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, must_field, is_main_alive


def test_strategies_list():
    """GET /api/strategies"""
    assert is_main_alive()
    code, body = get("/api/strategies")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "strategies" in j or "ok" in j


def test_strategy_run_code():
    """GET /api/strategies/run/600036 容许 200/404"""
    code, body = get("/api/strategies/run/600036")
    assert code in (200, 404, 405)
