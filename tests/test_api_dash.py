"""tests/test_api_dash.py · T-003 · dash blueprint 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import must_status, must_field, get, is_main_alive


def test_dash_root():
    """GET / 返回 dashboard HTML 200"""
    assert is_main_alive(), "主实例未启动"
    code, body = get("/")
    assert code == 200
    assert len(body) > 1000, f"dashboard HTML 异常短: {len(body)} bytes"


def test_dash_dashboard_route():
    """GET /dashboard 返回 dashboard HTML"""
    code, body = get("/dashboard")
    assert code == 200
    assert b"GBT Pro" in body or b"\xe5\x9f\xba\xe9\x87\x91" in body


def test_dash_api_status():
    """GET /api/status 返回当前运行角色"""
    j = must_field("/api/status", "role")
    assert j["role"] in ("dev", "desktop")
    assert "ok" in j and j["ok"] is True
    assert "mcp_count" in j
    assert "version" in j


def test_dash_api_system():
    """GET /api/system"""
    code, body = get("/api/system")
    assert code == 200


def test_dash_api_dashboard_data():
    """GET /api/dashboard 返回仪表盘数据"""
    code, body = get("/api/dashboard")
    assert code == 200
    import json
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "users" in j or "system" in j or "mcp" in j


def test_dash_styles_css():
    """GET /styles.css 返回 CSS"""
    code, body = get("/styles.css")
    assert code == 200
    assert b"css" in body[:200].lower() or b"{" in body


def test_dash_favicon():
    """GET /favicon.ico 返回 200/204"""
    code, _ = get("/favicon.ico")
    assert code in (200, 204)
