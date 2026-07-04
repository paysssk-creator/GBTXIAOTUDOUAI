"""tests/test_api_mirror.py · T-003 · mirror blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, post, must_field, is_main_alive


def test_mirror_status():
    """GET /api/mirror/status 返回插件状态，且不暴露绝对路径"""
    assert is_main_alive()
    j = must_field("/api/mirror/status", "info")
    info = j["info"]
    assert "skills" in info
    assert isinstance(info["skills"], list)
    assert "ok" in info
    assert info["ok"] is True
    assert "C:\\" not in json.dumps(info, ensure_ascii=False)


def test_mirror_skills():
    """GET /api/mirror/skills 返回镜像信息，且不暴露绝对路径"""
    j = must_field("/api/mirror/skills", "ok")
    assert j["ok"] is True
    assert "skills" in j
    assert "modules" in j
    assert "C:\\" not in json.dumps(j, ensure_ascii=False)


def test_mirror_invoke_status_skill():
    """POST /api/mirror/invoke 调用 status skill"""
    code, body = post("/api/mirror/invoke", {"skill": "status", "dry_run": True})
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True


def test_mirror_invoke_validate_returns_quickly():
    """POST /api/mirror/invoke validate 不应挂死，并返回结构化结果"""
    code, body = post("/api/mirror/invoke", {"skill": "validate", "dry_run": True}, timeout=20)
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j
    assert "result" in j
    assert "C:\\" not in json.dumps(j, ensure_ascii=False)


def test_mirror_invoke_unknown_skill():
    """POST /api/mirror/invoke 调用未知 skill"""
    code, body = post("/api/mirror/invoke", {"skill": "made_up_xxx", "dry_run": True})
    # 服务端对 unknown skill 返回 400 + ok=false
    assert code in (200, 400)
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j
