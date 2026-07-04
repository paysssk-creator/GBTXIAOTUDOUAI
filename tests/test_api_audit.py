"""tests/test_api_audit.py · T-003 · audit blueprint 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, is_main_alive


def test_audit_main():
    """GET /api/audit 返回审计数据"""
    assert is_main_alive()
    code, body = get("/api/audit")
    assert code == 200


def test_audit_alert_log():
    """GET /api/alert/log"""
    code, body = get("/api/alert/log")
    assert code == 200


def test_audit_access_log():
    """GET /api/access_log"""
    code, body = get("/api/access_log")
    assert code == 200
