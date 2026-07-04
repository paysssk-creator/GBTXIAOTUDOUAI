"""tests/test_payment_futurapay.py · 付费模块已下线"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import pytest

from _bp_helper import get, post, is_main_alive  # noqa: E402


def _assert_removed(code, body):
    assert code == 410
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j.get("ok") is False
    assert j.get("removed") is True
    assert "已下线" in (j.get("error") or "")


def test_payment_http_status_removed():
    """GET /api/payment/status 应明确返回已下线"""
    if not is_main_alive():
        pytest.skip("desktop_app.py 未运行在 :8765")
    code, body = get("/api/payment/status")
    _assert_removed(code, body)


def test_payment_http_link_removed():
    """POST /api/payment/link 应明确返回已下线"""
    if not is_main_alive():
        pytest.skip("desktop_app.py 未运行在 :8765")
    code, body = post("/api/payment/link", {
        "amount": 10,
        "currency": "USD",
        "first_name": "Test",
        "last_name": "User",
        "email": "t@e.com",
        "country_code": "US",
    })
    _assert_removed(code, body)


def test_payment_http_probe_removed():
    """POST /api/payment/probe 应明确返回已下线"""
    if not is_main_alive():
        pytest.skip("desktop_app.py 未运行在 :8765")
    code, body = post("/api/payment/probe", {"url": "https://example.com"})
    _assert_removed(code, body)


def test_payment_http_orders_removed():
    """GET /api/payment/orders 应明确返回已下线"""
    if not is_main_alive():
        pytest.skip("desktop_app.py 未运行在 :8765")
    code, body = get("/api/payment/orders")
    _assert_removed(code, body)
