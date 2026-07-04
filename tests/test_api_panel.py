"""tests/test_api_panel.py · T-003 · panel blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, must_field, is_main_alive


def test_panel_status():
    """GET /api/panel/status 返回面板状态，且不暴露绝对路径"""
    assert is_main_alive()
    j = must_field("/api/panel/status", "ok")
    assert j["ok"] is True
    assert "role" in j
    assert "version" in j
    assert j["role"] in ("dev", "desktop")
    assert "C:\\" not in json.dumps(j, ensure_ascii=False)
