"""tests/test_api_account.py · T-003 · account blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, post, must_field, is_main_alive


def test_account_main():
    """GET /api/account 返回账户信息"""
    assert is_main_alive()
    j = must_field("/api/account", "ok")
    assert j["ok"] is True


def test_account_trades():
    """GET /api/account/trades"""
    code, body = get("/api/account/trades")
    assert code in (200, 401)


def test_account_positions():
    """GET /api/account/positions"""
    code, body = get("/api/account/positions")
    assert code in (200, 401)


def test_token_balance():
    """GET /api/token/balance 返回余额（实际字段：tokens/used/remaining/plan）"""
    j = must_field("/api/token/balance", "ok")
    assert j["ok"] is True
    assert "tokens" in j or "remaining" in j


def test_token_plans():
    """GET /api/token/plans"""
    code, body = get("/api/token/plans")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "plans" in j or "ok" in j


def test_token_recharge_validation():
    """POST /api/token/recharge 应明确返回已下线"""
    code, body = post("/api/token/recharge", {})
    assert code == 410
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j.get("ok") is False
    assert j.get("removed") is True
    assert "付费模块已下线" in (j.get("error") or "")
