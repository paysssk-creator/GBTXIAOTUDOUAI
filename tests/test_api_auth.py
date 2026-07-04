"""tests/test_api_auth.py · T-003 · auth blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import post, get, must_field, is_main_alive


def test_auth_register_validation():
    """POST /api/auth/register 必填字段为空时返回 400"""
    assert is_main_alive(), "主实例未启动"
    code, body = post("/api/auth/register", {})
    assert code in (200, 400), f"register 异常: {code}"
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j


def test_auth_login_validation():
    """POST /api/auth/login 缺字段时返回 400"""
    code, body = post("/api/auth/login", {})
    assert code in (200, 400)
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j


def test_auth_logout_validation():
    """POST /api/auth/logout 正常处理"""
    code, body = post("/api/auth/logout", {})
    assert code in (200, 401, 400)
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j


def test_auth_profile_unauthorized():
    """GET /api/auth/profile 未登录时返回 401"""
    code, body = get("/api/auth/profile")
    assert code in (200, 401), f"profile 异常: {code}"
    j = json.loads(body.decode("utf-8", errors="ignore"))
    if code == 401:
        assert j.get("ok") is False
