"""tests/test_api_desktop.py · T-003 · desktop blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, post, is_main_alive


def test_url_scheme():
    """GET /api/url_scheme"""
    assert is_main_alive()
    code, body = get("/api/url_scheme")
    assert code in (200, 400, 405)


def test_desktop_control_stack():
    """GET /api/desktop/control-stack 返回九栈兼容报告"""
    assert is_main_alive()
    code, body = get("/api/desktop/control-stack")
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["primary_controller"] == "native_desktop"
    assert int(j["summary"]["total_external_stacks"]) == 9


def test_desktop_exec_browser_open_dry_run():
    """POST /api/desktop/exec 支持 dry_run 预演浏览器打开"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "browser_open",
        "query": "东方财富 A股",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert "预演打开浏览器" in (j.get("data") or "")


def test_desktop_exec_keyboard_type_dry_run():
    """POST /api/desktop/exec 支持键盘输入预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "keyboard_type",
        "text": "hello",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("typed_text") == "hello"


def test_desktop_exec_keyboard_hotkey_dry_run():
    """POST /api/desktop/exec 支持快捷键预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "keyboard_hotkey",
        "keys": ["ctrl", "s"],
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("keys") == ["ctrl", "s"]


def test_desktop_exec_mouse_click_dry_run():
    """POST /api/desktop/exec 支持鼠标点击预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "mouse_click",
        "x": 100,
        "y": 100,
        "button": "left",
        "clicks": 1,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("button") == "left"


def test_desktop_exec_mouse_move_dry_run():
    """POST /api/desktop/exec 支持鼠标移动预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "mouse_move",
        "x": 200,
        "y": 150,
        "duration": 0.1,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("x") == 200
    assert j.get("y") == 150


def test_desktop_exec_trade_form_fill_dry_run():
    """POST /api/desktop/exec 可预演交易填单，不直接输入"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_form_fill",
        "stock_code": "600519",
        "price": 1420.55,
        "lots": 100,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert "预演填单" in (j.get("data") or "")


def test_desktop_exec_process_kill_requires_confirm():
    """POST /api/desktop/exec 高风险进程结束需明确确认"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "process_kill",
        "name": "notepad",
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is False
    assert j["requires_confirmation"] is True


def test_desktop_exec_broker_window_scan():
    """POST /api/desktop/exec 支持券商窗口扫描"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "broker_window_scan",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "windows" in j
    assert "observed_titles" in j


def test_desktop_exec_trade_ready_check():
    """POST /api/desktop/exec 返回操盘准备检查结果"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_ready_check",
        "broker": "东方财富",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "window_state" in j
    assert "login_state" in j
    assert "anchor_state" in j
    assert "entrust_state" in j
    assert "position_state" in j


def test_desktop_exec_trade_anchor_detect():
    """POST /api/desktop/exec 支持交易锚点识别"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_anchor_detect",
        "trade_action": "buy",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "anchors" in j


def test_desktop_exec_trade_anchor_detect_with_broker():
    """POST /api/desktop/exec 交易锚点识别支持券商适配参数"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_anchor_detect",
        "broker": "同花顺",
        "trade_action": "buy",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j.get("broker") == "同花顺"


def test_desktop_exec_trade_confirm_detect():
    """POST /api/desktop/exec 支持确认弹窗识别"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_confirm_detect",
        "trade_action": "buy",
        "stock_code": "600519",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "confirm_state" in j


def test_desktop_exec_trade_entrust_readback():
    """POST /api/desktop/exec 支持委托区域回读"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_entrust_readback",
        "stock_code": "600519",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "entrust_state" in j
    assert "rows" in j["entrust_state"]
    assert "summary" in j["entrust_state"]


def test_desktop_exec_trade_position_readback():
    """POST /api/desktop/exec 支持持仓区域回读"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_position_readback",
        "stock_code": "600519",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "position_state" in j
    assert "rows" in j["position_state"]
    assert "summary" in j["position_state"]


def test_desktop_exec_trade_ready_check_with_broker():
    """POST /api/desktop/exec 操盘准备检查支持券商适配参数"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_ready_check",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j.get("broker") == "同花顺"
    assert "entrust_state" in j
    assert "position_state" in j
    assert "rows" in j["entrust_state"]
    assert "rows" in j["position_state"]


def test_desktop_exec_trade_takeover_ready():
    """POST /api/desktop/exec 支持自主接管准备检查"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_ready",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "takeover_phase" in j
    assert "next_step" in j
    assert "window_state" in j
    assert "login_state" in j
    assert "page_nav_state" in j
    assert "entrust_state" in j
    assert "position_state" in j


def test_desktop_exec_trade_takeover_ready_dry_run():
    """POST /api/desktop/exec 支持自主接管准备预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_ready",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("auto_focus") is True
    assert j.get("auto_navigate") is True


def test_desktop_exec_trade_takeover_watch():
    """POST /api/desktop/exec 支持持续接管监视"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_watch",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "timeout_sec": 5,
        "poll_interval": 1,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "timeline" in j
    assert "elapsed" in j
    assert "takeover_phase" in j
    assert "page_nav_state" in j


def test_desktop_exec_trade_takeover_watch_dry_run():
    """POST /api/desktop/exec 支持持续接管监视预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_watch",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "timeout_sec": 12,
        "poll_interval": 2,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("timeout_sec") == 12
    assert j.get("poll_interval") == 2
    assert j.get("auto_focus") is True
    assert j.get("auto_navigate") is True


def test_desktop_exec_trade_takeover_precheck():
    """POST /api/desktop/exec 支持接管后预检"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_precheck",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "price": 1420.55,
        "lots": 100,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "takeover_phase" in j
    assert "confirm_state" in j
    assert "risk_gate" in j
    assert "supported_actions" in j
    assert "can_fill_form" in j
    assert "next_action_id" in j


def test_desktop_exec_trade_takeover_precheck_app_only():
    """POST /api/desktop/exec 支持 APP 内闭环预检"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_precheck",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "price": 1420.55,
        "lots": 100,
        "app_only": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["app_only"] is True
    assert j["takeover_phase"] == "app_only"
    assert j["precheck_passed"] is True
    assert j["next_action_id"] == "trade_form_fill"



def test_desktop_exec_trade_takeover_precheck_dry_run():
    """POST /api/desktop/exec 支持接管后预检预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_takeover_precheck",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "price": 1420.55,
        "lots": 100,
        "capture_evidence": True,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert j.get("capture_evidence") is True
    assert "supported_actions" in j
    assert "risk_gate" in j
    assert "evidence" in j
    assert "screenshots/" in (j["evidence"].get("screenshot_path") or "")
    assert "audit_evidence/" in (j["evidence"].get("report_path") or "")


def test_desktop_exec_trade_panel_probe():
    """POST /api/desktop/exec 支持聚焦后联合回读探测"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_panel_probe",
        "broker": "同花顺",
        "stock_code": "600519",
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert "entrust_state" in j
    assert "position_state" in j
    assert "window_state" in j
    assert "anchor_state" in j


def test_desktop_exec_trade_panel_probe_dry_run_with_evidence():
    """POST /api/desktop/exec 支持联合回读证据包预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_panel_probe",
        "broker": "同花顺",
        "stock_code": "600519",
        "dry_run": True,
        "capture_evidence": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
    assert "evidence" in j
    assert "screenshots/" in (j["evidence"].get("screenshot_path") or "")
    assert "audit_evidence/" in (j["evidence"].get("report_path") or "")


def test_desktop_exec_trade_execute_next_app_only_defaults_to_fill_preview():
    """POST /api/desktop/exec 支持服务端自动执行唯一下一步"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_execute_next",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "price": 1420.55,
        "lots": 100,
        "app_only": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["executed_action"] == "trade_form_fill"
    assert j["dry_run"] is True
    assert j["auto_selected"] is True
    assert j["precheck"]["next_action_id"] == "trade_form_fill"


def test_desktop_exec_trade_live_validate_app_only_with_confirm_archives_evidence():
    """POST /api/desktop/exec 支持闭环验证与证据归档"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_live_validate",
        "broker": "同花顺",
        "stock_code": "600519",
        "trade_action": "buy",
        "price": 1420.55,
        "lots": 100,
        "app_only": True,
        "confirm": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["validation_state"]["passed"] is True
    assert j["form_result"]["ok"] is True
    assert j["submit_result"]["ok"] is True
    assert j["watch_result"]["ok"] is True
    assert "screenshots/" in (j["evidence"].get("screenshot_path") or "")
    assert "audit_evidence/" in (j["evidence"].get("report_path") or "")


def test_desktop_exec_trade_submit_confirm_requires_confirm():
    """POST /api/desktop/exec 提交交易确认必须显式 confirm"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_submit_confirm",
        "trade_action": "buy",
        "stock_code": "600519",
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is False
    assert j["requires_confirmation"] is True


def test_desktop_exec_trade_submit_confirm_app_only():
    """POST /api/desktop/exec 支持 APP 内确认提交"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_submit_confirm",
        "trade_action": "buy",
        "stock_code": "600519",
        "app_only": True,
        "confirm": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["app_only"] is True
    assert j["confirm_state"]["found"] is True
    assert "APP内已确认提交" in (j.get("data") or "")


def test_desktop_exec_trade_result_watch_app_only():
    """POST /api/desktop/exec 支持 APP 内结果回看"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_result_watch",
        "trade_action": "buy",
        "stock_code": "600519",
        "app_only": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["app_only"] is True
    assert j["watch_state"]["found"] is True
    assert "600519" in (j["watch_state"].get("entrust_state", {}).get("codes") or [])



def test_desktop_exec_trade_result_watch_dry_run():
    """POST /api/desktop/exec 支持委托结果回看预演"""
    assert is_main_alive()
    code, body = post("/api/desktop/exec", {
        "id": "trade_result_watch",
        "trade_action": "buy",
        "stock_code": "600519",
        "timeout": 15,
        "dry_run": True,
    })
    assert code == 200
    j = json.loads(body.decode("utf-8", errors="ignore"))
    assert j["ok"] is True
    assert j["dry_run"] is True
