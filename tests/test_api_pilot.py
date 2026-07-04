"""tests/test_api_pilot.py · T-003 · pilot blueprint 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, is_main_alive


def test_pilot_status():
    """GET /api/pilot/status 返回操盘引擎状态"""
    assert is_main_alive()
    code, body = get("/api/pilot/status")
    assert code in (200, 503)


def test_pilot_signals():
    """GET /api/pilot/signals"""
    code, body = get("/api/pilot/signals")
    assert code in (200, 503)


def test_pilot_stop_safety():
    """GET /api/pilot/stop 容许 405 或 200"""
    code, body = get("/api/pilot/stop")
    assert code in (200, 405, 503)
