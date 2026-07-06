"""tests/test_api_llm.py · T-003 · llm blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, post, must_field, is_main_alive


def test_llm_get_config():
    """GET /api/config/llm 返回 LLM 配置（实际字段：available/current/model）"""
    assert is_main_alive()
    code, body = get("/api/config/llm")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "available" in j or "current" in j or "model" in j
    assert "saved_on_device" in j


def test_llm_post_config_validation():
    """POST /api/config/llm 接 body"""
    code, body = post("/api/config/llm", {"provider": "deepseek"})
    assert code in (200, 400)
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert "ok" in j


def test_cloud_brain_get_config():
    """GET /api/config/cloud_brain 返回云端大脑配置"""
    assert is_main_alive()
    code, body = get("/api/config/cloud_brain")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "url" in j
    assert "chat_mode" in j
    assert "status" in j


def test_llm_chat_validation():
    """POST /api/chat 缺字段处理"""
    code, body = post("/api/chat", {})
    assert code in (200, 400)


def test_llm_chat_capability_scope_query():
    """POST /api/chat 询问电脑操控能力时走本地能力答复，不应回“无法直接操控电脑”"""
    code, body = post("/api/chat", {"text": "你现在操控电脑操作的达到什么程度了"})
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["model"] == "capability-registry"
    assert "无法直接操控电脑" not in (j.get("response") or "")
    assert "电脑直接操作" in (j.get("response") or "")
    assert "外部操控栈" in (j.get("response") or "")



def test_llm_chat_browser_open_routes_to_desktop_exec_dry_run():
    """POST /api/chat 命中打开浏览器指令时应转到真实桌面执行链"""
    code, body = post("/api/chat", {"text": "打开东方财富", "dry_run": True})
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["model"] == "desktop-executor"
    assert j["executed_action"] == "browser_open"
    assert "预演打开" in (j.get("response") or "")


def test_llm_chat_keyboard_type_routes_to_desktop_exec_dry_run():
    """POST /api/chat 命中输入指令时应走键盘输入执行链"""
    code, body = post("/api/chat", {"text": "输入 hello gbt", "dry_run": True})
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["model"] == "desktop-executor"
    assert j["executed_action"] == "keyboard_type"
    assert "预演键盘输入" in (j.get("response") or "")


def test_llm_chat_trade_precheck_routes_to_real_chain_dry_run():
    """POST /api/chat 命中操盘指令时应路由到真实操盘预检链，而不是虚拟问答"""
    code, body = post("/api/chat", {"text": "买入 600519 价格 1420.55 数量 100", "dry_run": True})
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["model"] == "desktop-executor"
    assert j["executed_action"] == "trade_takeover_precheck"
    assert "预演接管后预检" in (j.get("response") or "")
