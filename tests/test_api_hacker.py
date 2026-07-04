"""tests/test_api_hacker.py · 黑客模块已下线"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, post, is_main_alive


def test_hacker_capabilities_removed():
    """GET /api/hacker/capabilities 应明确返回已下线"""
    assert is_main_alive()
    code, body = get("/api/hacker/capabilities")
    assert code == 410
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j.get("ok") is False
    assert j.get("removed") is True
    assert "已下线" in (j.get("error") or "")


def test_hacker_exec_removed():
    """POST /api/hacker/exec 应明确拒绝，不再承载电脑操控能力"""
    assert is_main_alive()
    code, body = post("/api/hacker/exec", {"id": "screenshot", "action": "运行"}, timeout=30)
    assert code == 410
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j.get("ok") is False
    assert j.get("removed") is True
    assert "电脑操控" in (j.get("error") or "")
