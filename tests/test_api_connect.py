"""tests/test_api_connect.py · T-003 · connect blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, must_field, is_main_alive


def test_connect_providers():
    """GET /api/providers 返回 provider 列表（实际返回 provider id 列表为顶层 key）"""
    assert is_main_alive()
    code, body = get("/api/providers")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    # 实际：返回 { provider_id: { name, status, models } } 字典
    assert isinstance(j, dict) and len(j) >= 1


def test_connect_logo():
    """GET /api/logo 返回 logo"""
    code, body = get("/api/logo")
    assert code == 200


def test_connect_devices():
    """GET /api/devices"""
    code, body = get("/api/devices")
    assert code == 200


def test_connect_watcher_status():
    """GET /api/watcher/status"""
    code, body = get("/api/watcher/status")
    assert code == 200


def test_connect_trader_status():
    """GET /api/trader/status"""
    code, body = get("/api/trader/status")
    assert code == 200


def test_connect_connectors():
    """GET /api/connectors（实际返回 {connectors, total}）"""
    code, body = get("/api/connectors")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "connectors" in j
    assert "total" in j
