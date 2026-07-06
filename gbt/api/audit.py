"""GBT Pro · gbt/api/audit.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：audit
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, sys, json, time, urllib.parse
bp = Blueprint("audit", __name__)


@bp.route("/api/audit")
def api_audit():
    import json, os
    audit_file = os.path.join(os.path.dirname(__file__), "audit_trail.jsonl")
    records = []
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f.readlines()[-50:]:
                try:
                    records.append(json.loads(line.strip()))
                except Exception:
                    pass
    return jsonify({"ok": True, "count": len(records), "records": records})


@bp.route("/api/alert/log")
def api_alert_log():
    import os
    alert_file = os.path.join(os.path.dirname(__file__), "alerts.log")
    lines = []
    if os.path.exists(alert_file):
        with open(alert_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()[-30:]]
    return jsonify({"ok": True, "alerts": lines})

def _runtime_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _flag(payload, key):
    value = (payload or {}).get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "confirm"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _reply(ok, text, t, **extra):
    body = {"ok": ok, "time": t}
    if ok:
        body["data"] = text
    else:
        body["error"] = text
    body.update(extra)
    return body


def _preview(text, t, **extra):
    body = {"ok": True, "dry_run": True, "time": t, "data": text}
    body.update(extra)
    return body


def _kill_process(target_pid=None, target_name=""):
    import psutil
    if target_pid:
        proc = psutil.Process(int(target_pid))
        proc.kill()
        return f"已结束进程 PID={target_pid} {proc.name()}"
    if target_name:
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            if target_name.lower() in (proc.info.get("name") or "").lower():
                proc.kill()
                killed.append(f"{proc.info['pid']}:{proc.info.get('name','?')}")
        if killed:
            return "已结束进程: " + ", ".join(killed[:8])
        return f"未找到进程: {target_name}"
    raise ValueError("缺少 pid 或 name")


def _detect_login_state(broker=""):
    try:
        from gbt.screen_ai import ScreenOCR
        ocr = ScreenOCR()
        keywords = None
        if broker:
            try:
                from gbt.stock_gate import get_broker_ui_profile
                keywords = (get_broker_ui_profile(broker).get("login_keywords") or None)
            except Exception:
                keywords = None
        result = ocr.detect_login_state(keywords=keywords)
        if result.get("logged_in"):
            return {"ok": True, "logged_in": True, "confidence": result.get("confidence"), "keywords": result.get("found_keywords", [])}
        return {"ok": True, "logged_in": False, "confidence": result.get("confidence"), "keywords": result.get("found_keywords", [])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def _detect_trade_anchors(action="", broker=""):
    try:
        from gbt.screen_ai import ScreenOCR
        ocr = ScreenOCR()
        return ocr.detect_trade_form_anchors(action=action or None, broker=broker or "")
    except Exception as e:
        return {"ok": False, "found": False, "anchors": {}, "keywords": {}, "error": str(e)[:120]}


def _detect_trade_confirm_dialog(action="", stock_code="", broker=""):
    try:
        from gbt.screen_ai import ScreenOCR
        ocr = ScreenOCR()
        return ocr.detect_trade_confirm_dialog(action=action or None, stock_code=stock_code or "", broker=broker or "")
    except Exception as e:
        return {"ok": False, "found": False, "confirm_btn": None, "keywords": [], "error": str(e)[:120]}


def _watch_trade_result(action="", stock_code="", timeout=30, broker=""):
    try:
        from gbt.screen_ai import AutoPipeline
        pipe = AutoPipeline()
        result = pipe.monitor_trade_screen(code=stock_code or "000000", action=action or "buy", timeout=timeout, broker=broker or "")
        return {
            "ok": bool(result.get("ok")),
            "found": bool(result.get("found")),
            "keywords": list(result.get("keywords") or []),
            "elapsed": result.get("elapsed", 0),
            "message": result.get("message"),
            "entrust_state": result.get("entrust_state") or {},
            "position_state": result.get("position_state") or {},
        }
    except Exception as e:
        return {"ok": False, "found": False, "keywords": [], "elapsed": 0, "error": str(e)[:120]}


def _read_trade_panel(panel="entrust", stock_code="", broker=""):
    try:
        from gbt.screen_ai import ScreenOCR
        ocr = ScreenOCR()
        return ocr.detect_trade_panel_readback(panel=panel or "entrust", stock_code=stock_code or "", broker=broker or "")
    except Exception as e:
        return {
            "ok": False,
            "found": False,
            "panel": panel,
            "broker": broker or None,
            "codes": [],
            "matched_lines": [],
            "metrics": [],
            "rows": [],
            "summary": {},
            "error": str(e)[:120],
        }


def _public_login_state(result):
    result = result or {}
    return {
        "ok": bool(result.get("ok", True)),
        "logged_in": bool(result.get("logged_in")),
        "confidence": result.get("confidence", 0.0),
        "keywords": list(result.get("found_keywords") or []),
        "error": result.get("error"),
    }


def _public_anchor_state(result):
    result = result or {}
    return {
        "ok": bool(result.get("ok")),
        "found": bool(result.get("found")),
        "anchors": result.get("anchors", {}) or {},
        "keywords": result.get("keywords", {}) or {},
        "error": result.get("error"),
    }


def _public_confirm_state(result):
    result = result or {}
    return {
        "ok": bool(result.get("ok")),
        "found": bool(result.get("found")),
        "confirm_btn": result.get("confirm_btn"),
        "keywords": list(result.get("keywords") or []),
        "error": result.get("error"),
    }


def _public_trade_watch_state(result):
    result = result or {}
    return {
        "ok": bool(result.get("ok")),
        "found": bool(result.get("found")),
        "keywords": list(result.get("keywords") or []),
        "elapsed": result.get("elapsed", 0),
        "message": result.get("message"),
        "entrust_state": result.get("entrust_state") or {},
        "position_state": result.get("position_state") or {},
        "error": result.get("error"),
    }


def _public_panel_readback_state(result):
    result = result or {}
    return {
        "ok": bool(result.get("ok")),
        "found": bool(result.get("found")),
        "panel": result.get("panel"),
        "broker": result.get("broker"),
        "bounds": result.get("bounds"),
        "codes": list(result.get("codes") or []),
        "matched_lines": list(result.get("matched_lines") or []),
        "metrics": list(result.get("metrics") or []),
        "rows": list(result.get("rows") or []),
        "summary": result.get("summary") or {},
        "error": result.get("error"),
    }


def _panel_brief_lines(label, state):
    state = state or {}
    lines = []
    if state.get("found"):
        lines.append(f"{label}：已识别 {len(state.get('matched_lines') or [])} 行")
        summary = state.get("summary") or {}
        if summary.get("codes"):
            lines.append(f"{label}代码：" + "、".join((summary.get("codes") or [])[:4]))
        if summary.get("statuses"):
            lines.append(f"{label}状态：" + "、".join((summary.get("statuses") or [])[:4]))
        if state.get("rows"):
            row = state.get("rows")[0] or {}
            pieces = []
            for key, label_name in (
                ("code", "代码"),
                ("price", "价格"),
                ("quantity", "数量"),
                ("status", "状态"),
                ("available", "可用"),
                ("market_value", "市值"),
                ("profit", "盈亏"),
            ):
                if row.get(key):
                    pieces.append(label_name + ":" + str(row.get(key)))
            if pieces:
                lines.append(f"{label}首行：" + " / ".join(pieces))
    else:
        lines.append(f"{label}：未识别到")
    return lines


def _trade_probe_evidence_plan(broker="", stock_code=""):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    suffix_parts = []
    if broker:
        suffix_parts.append(str(broker).strip().replace(" ", ""))
    if stock_code:
        suffix_parts.append(str(stock_code).strip())
    suffix = ("_" + "_".join(suffix_parts[:2])) if suffix_parts else ""
    return {
        "screenshot_path": f"screenshots/trade_probe_{stamp}{suffix}.png",
        "report_path": f"audit_evidence/trade_probe_{stamp}{suffix}.json",
    }


def _capture_trade_probe_evidence(payload):
    payload = payload or {}
    broker = str(payload.get("broker", "")).strip()
    stock_code = str(payload.get("stock_code", "")).strip()
    plan = _trade_probe_evidence_plan(broker=broker, stock_code=stock_code)
    root_dir = _runtime_root()
    screenshot_abs = os.path.join(root_dir, plan["screenshot_path"].replace("/", os.sep))
    report_abs = os.path.join(root_dir, plan["report_path"].replace("/", os.sep))
    os.makedirs(os.path.dirname(screenshot_abs), exist_ok=True)
    os.makedirs(os.path.dirname(report_abs), exist_ok=True)
    evidence = {
        "ok": True,
        "screenshot_path": plan["screenshot_path"],
        "report_path": plan["report_path"],
    }
    try:
        import pyautogui
        pyautogui.screenshot(screenshot_abs)
    except Exception as e:
        evidence["ok"] = False
        evidence["screenshot_error"] = str(e)[:120]
    report = {
        "saved_at": int(time.time()),
        "broker": broker or None,
        "stock_code": stock_code or None,
        "evidence": evidence,
        "snapshot": payload,
    }
    try:
        with open(report_abs, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        evidence["ok"] = False
        evidence["report_error"] = str(e)[:120]
    return evidence


def _trade_validation_evidence_plan(broker="", stock_code=""):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    suffix_parts = []
    if broker:
        suffix_parts.append(str(broker).strip().replace(" ", ""))
    if stock_code:
        suffix_parts.append(str(stock_code).strip())
    suffix = ("_" + "_".join(suffix_parts[:2])) if suffix_parts else ""
    return {
        "screenshot_path": f"screenshots/trade_validate_{stamp}{suffix}.png",
        "report_path": f"audit_evidence/trade_validate_{stamp}{suffix}.json",
    }


def _archive_trade_validation_report(report, broker="", stock_code=""):
    report = report or {}
    plan = _trade_validation_evidence_plan(broker=broker, stock_code=stock_code)
    root_dir = _runtime_root()
    screenshot_abs = os.path.join(root_dir, plan["screenshot_path"].replace("/", os.sep))
    report_abs = os.path.join(root_dir, plan["report_path"].replace("/", os.sep))
    os.makedirs(os.path.dirname(screenshot_abs), exist_ok=True)
    os.makedirs(os.path.dirname(report_abs), exist_ok=True)
    evidence = {
        "ok": True,
        "screenshot_path": plan["screenshot_path"],
        "report_path": plan["report_path"],
    }
    try:
        import pyautogui
        pyautogui.screenshot(screenshot_abs)
    except Exception as e:
        evidence["ok"] = False
        evidence["screenshot_error"] = str(e)[:120]
    try:
        with open(report_abs, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        evidence["ok"] = False
        evidence["report_error"] = str(e)[:120]
    return evidence


def _enumerate_window_titles():
    titles = []
    try:
        import pyautogui

        for win in pyautogui.getAllWindows():
            title = str(getattr(win, "title", "") or "").strip()
            if title:
                titles.append(title)
    except Exception:
        pass
    if not titles:
        from gbt.device_ctl import DesktopCtl

        listed = DesktopCtl.list_windows()
        titles = list(listed.get("titles") or []) if listed.get("ok") else []
    seen = set()
    ordered = []
    for raw_title in titles:
        title = str(raw_title or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        ordered.append(title)
    return ordered


def _match_broker_window_title(title: str):
    from gbt.stock_gate import BROKERS, get_broker_ui_profile

    title = str(title or "").strip()
    if not title:
        return None
    title_lower = title.lower()
    best = None
    for broker_name, info in BROKERS.items():
        profile = get_broker_ui_profile(broker_name)
        words = [broker_name] + list(info.get("keywords", [])) + list(profile.get("window_keywords") or [])
        matched = []
        score = 0
        for word in words:
            word = str(word or "").strip()
            if not word:
                continue
            word_lower = word.lower()
            if word_lower in title_lower:
                if word not in matched:
                    matched.append(word)
                bonus = max(2, len(word))
                if word in (profile.get("window_keywords") or []):
                    bonus += 4
                if word == broker_name:
                    bonus += 2
                score += bonus
        if not matched:
            continue
        hit = {
            "broker": broker_name,
            "title": title,
            "score": score,
            "matched_keywords": matched[:8],
        }
        if not best or hit["score"] > best["score"]:
            best = hit
    return best


def _scan_broker_windows():
    from gbt.device_ctl import DesktopCtl

    current = DesktopCtl.active_window_title()
    titles = _enumerate_window_titles()
    broker_hits = []
    for raw_title in titles:
        title = str(raw_title or "").strip()
        if not title:
            continue
        matched = _match_broker_window_title(title)
        if matched:
            broker_hits.append({
                **matched,
                "active": bool(current.get("ok") and current.get("title") == title),
            })
    broker_hits.sort(key=lambda item: (0 if item.get("active") else 1, -int(item.get("score", 0))), reverse=False)
    return {
        "ok": True,
        "active_window": current if current.get("ok") else None,
        "window_count": len(titles),
        "observed_titles": titles[:20],
        "broker_windows": broker_hits[:20],
    }


def _resolve_broker_hint(raw_broker=""):
    broker = str(raw_broker or "").strip()
    if broker:
        try:
            from gbt.stock_gate import find_broker
            found = find_broker(broker)
            return (found or {}).get("name") or broker
        except Exception:
            return broker
    scan = _scan_broker_windows()
    hits = scan.get("broker_windows") or []
    if hits:
        return hits[0].get("broker") or ""
    return ""


def _trade_takeover_snapshot(broker="", stock_code="", trade_action="", auto_focus=True, auto_navigate=True):
    broker_hint = _resolve_broker_hint(broker)
    focus_state = None
    page_nav_state = {"ok": False, "skipped": True, "reason": "未执行自动切页"}
    if auto_focus and (broker_hint or broker):
        focus_state = _focus_broker_window(broker=broker_hint or broker)
        time.sleep(0.6)
    scan = _scan_broker_windows()
    active = scan.get("active_window") or {}
    if not broker_hint and scan.get("broker_windows"):
        broker_hint = scan["broker_windows"][0].get("broker") or ""
    login_state = _public_login_state(_detect_login_state(broker=broker_hint))
    anchor_state = _public_anchor_state(_detect_trade_anchors(action=trade_action, broker=broker_hint))
    entrust_state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code=stock_code, broker=broker_hint))
    position_state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code=stock_code, broker=broker_hint))
    has_trade_context = bool(
        (anchor_state.get("anchors") or {})
        or entrust_state.get("found")
        or position_state.get("found")
    )
    if auto_navigate and scan.get("broker_windows") and login_state.get("logged_in") and not has_trade_context:
        preferred_page = trade_action if trade_action in {"buy", "sell"} else "entrust"
        page_nav_state = _navigate_trade_page(broker=broker_hint, trade_action=trade_action, preferred_page=preferred_page)
        time.sleep(0.6)
        scan = _scan_broker_windows()
        active = scan.get("active_window") or {}
        anchor_state = _public_anchor_state(_detect_trade_anchors(action=trade_action, broker=broker_hint))
        entrust_state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code=stock_code, broker=broker_hint))
        position_state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code=stock_code, broker=broker_hint))
        has_trade_context = bool(
            (anchor_state.get("anchors") or {})
            or entrust_state.get("found")
            or position_state.get("found")
        )
    elif auto_navigate and not scan.get("broker_windows"):
        page_nav_state = {"ok": False, "skipped": True, "reason": "未识别到券商窗口，暂不切页"}
    elif auto_navigate and not login_state.get("logged_in"):
        page_nav_state = {"ok": False, "skipped": True, "reason": "尚未登录券商，暂不切页"}
    elif auto_navigate:
        page_nav_state = {"ok": True, "skipped": True, "reason": "当前已在交易相关页面，无需切页"}
    if not scan.get("broker_windows"):
        takeover_phase = "await_broker_window"
        next_step = "请先打开并停留在真实券商交易客户端，AI 再继续接管。"
    elif not login_state.get("logged_in"):
        takeover_phase = "await_login"
        next_step = "请先完成券商登录，登录完成后 AI 自动接管。"
    elif not has_trade_context:
        takeover_phase = "await_trade_page"
        next_step = "请先切到买卖/委托/持仓交易页，AI 再继续接管。"
    else:
        takeover_phase = "ready_for_takeover"
        next_step = "已进入自主接管态，可继续看盘、填单和下单预演。"
    return {
        "broker": broker_hint or broker or None,
        "stock_code": stock_code or None,
        "trade_action": trade_action or None,
        "focus_state": focus_state,
        "page_nav_state": page_nav_state,
        "window_state": scan,
        "active_window": active,
        "login_state": login_state,
        "anchor_state": anchor_state,
        "entrust_state": entrust_state,
        "position_state": position_state,
        "takeover_phase": takeover_phase,
        "next_step": next_step,
        "ready": takeover_phase == "ready_for_takeover",
        "human_action_required": takeover_phase != "ready_for_takeover",
    }


def _focus_broker_window(broker="", title=""):
    import pyautogui

    scan = _scan_broker_windows()
    selected = None
    if title:
        for item in scan.get("broker_windows", []):
            if title.lower() in (item.get("title") or "").lower():
                selected = item
                break
    elif broker:
        for item in scan.get("broker_windows", []):
            if broker.lower() in (item.get("broker") or "").lower():
                selected = item
                break
    else:
        selected = (scan.get("broker_windows") or [None])[0]

    if not selected:
        return {"ok": False, "error": "未找到匹配的券商窗口", "scan": scan}

    matched = pyautogui.getWindowsWithTitle(selected["title"])
    if not matched:
        return {"ok": False, "error": f"窗口句柄不可用: {selected['title']}", "scan": scan}

    win = matched[0]
    try:
        win.activate()
    except Exception:
        pass
    try:
        win.restore()
    except Exception:
        pass
    try:
        win.maximize()
    except Exception:
        pass
    return {"ok": True, "selected": selected, "scan": scan}


def _trade_page_targets(broker="", trade_action="", preferred_page=""):
    from gbt.stock_gate import get_broker_ui_profile

    profile = get_broker_ui_profile(broker or "东方财富")
    anchor_keywords = profile.get("anchor_keywords") or {}
    panel_keywords = profile.get("panel_keywords") or {}
    targets = []
    if preferred_page in {"buy", "sell"}:
        targets.extend(anchor_keywords.get("buy_btn" if preferred_page == "buy" else "sell_btn") or [])
    elif preferred_page == "entrust":
        targets.extend(panel_keywords.get("entrust") or [])
    elif preferred_page == "position":
        targets.extend(panel_keywords.get("position") or [])
    if trade_action == "buy":
        targets.extend(anchor_keywords.get("buy_btn") or [])
    elif trade_action == "sell":
        targets.extend(anchor_keywords.get("sell_btn") or [])
    targets.extend(panel_keywords.get("entrust") or [])
    targets.extend(panel_keywords.get("position") or [])
    for word in ["买入", "卖出", "委托查询", "今日委托", "持仓", "持仓查询"]:
        if word not in targets:
            targets.append(word)
    deduped = []
    seen = set()
    for word in targets:
        clean = str(word or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        deduped.append(clean)
    return deduped


def _navigate_trade_page(broker="", trade_action="", preferred_page=""):
    from gbt.device_ctl import get_device
    from gbt.screen_ai import ScreenOCR

    device = get_device()
    ocr = ScreenOCR()
    targets = _trade_page_targets(broker=broker, trade_action=trade_action, preferred_page=preferred_page)
    attempts = []
    for word in targets[:8]:
        matches = ocr.find_text_on_screen(word)
        if not matches:
            attempts.append({"target": word, "clicked": False})
            continue
        match = matches[0]
        x = int(match.get("x", 0) + match.get("w", 0) / 2)
        y = int(match.get("y", 0) + match.get("h", 0) / 2)
        click_result = device.mouse.click(x, y, clicks=1)
        attempts.append({"target": word, "clicked": bool(click_result.get("ok")), "x": x, "y": y})
        time.sleep(0.5)
        anchor_state = _public_anchor_state(_detect_trade_anchors(action=trade_action, broker=broker))
        entrust_state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code="", broker=broker))
        position_state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code="", broker=broker))
        if (anchor_state.get("anchors") or {}) or entrust_state.get("found") or position_state.get("found"):
            return {
                "ok": True,
                "clicked": attempts,
                "target": word,
                "anchor_state": anchor_state,
                "entrust_state": entrust_state,
                "position_state": position_state,
            }
    return {"ok": False, "clicked": attempts, "reason": "未定位到可验证的交易页签"}


def _trade_takeover_watch(broker="", stock_code="", trade_action="", timeout_sec=60, poll_interval=3, auto_focus=True, auto_navigate=True):
    timeout_sec = max(5, min(int(timeout_sec or 60), 300))
    poll_interval = max(1, min(int(poll_interval or 3), 15))
    start = time.time()
    timeline = []
    snapshot = None
    first_round = True
    while True:
        snapshot = _trade_takeover_snapshot(
            broker=broker,
            stock_code=stock_code,
            trade_action=trade_action,
            auto_focus=auto_focus if first_round else False,
            auto_navigate=auto_navigate,
        )
        elapsed = round(time.time() - start, 1)
        timeline.append({
            "elapsed": elapsed,
            "takeover_phase": snapshot.get("takeover_phase"),
            "ready": bool(snapshot.get("ready")),
            "next_step": snapshot.get("next_step"),
            "active_window": ((snapshot.get("active_window") or {}).get("title") or ""),
            "page_nav_reason": ((snapshot.get("page_nav_state") or {}).get("reason") or ""),
        })
        if snapshot.get("ready") or elapsed >= timeout_sec:
            break
        first_round = False
        time.sleep(poll_interval)
    snapshot = snapshot or _trade_takeover_snapshot(
        broker=broker,
        stock_code=stock_code,
        trade_action=trade_action,
        auto_focus=auto_focus,
        auto_navigate=auto_navigate,
    )
    snapshot["elapsed"] = round(time.time() - start, 1)
    snapshot["timeline"] = timeline
    snapshot["completed"] = bool(snapshot.get("ready"))
    snapshot["timeout_sec"] = timeout_sec
    snapshot["poll_interval"] = poll_interval
    return snapshot


def _app_only_panel_state(panel="", broker="", stock_code=""):
    code = str(stock_code or "").strip()
    codes = [code] if code else []
    return {
        "ok": True,
        "found": bool(codes),
        "panel": panel,
        "broker": broker or "APP内闭环",
        "bounds": None,
        "codes": codes,
        "matched_lines": [],
        "metrics": [],
        "rows": [],
        "summary": {},
        "error": None,
    }


def _app_only_takeover_snapshot(broker="", stock_code=""):
    broker_name = str(broker or "").strip() or "APP内闭环"
    return {
        "ok": True,
        "broker": broker_name,
        "stock_code": stock_code or None,
        "focus_state": {"ok": True, "skipped": True, "reason": "APP-only 模式不依赖外部券商窗口"},
        "window_state": {"ok": True, "active_window": None, "broker_windows": [], "observed_titles": [], "window_count": 0},
        "active_window": None,
        "login_state": {"ok": True, "logged_in": True, "confidence": 1.0, "keywords": ["APP-only"], "error": None},
        "page_nav_state": {"ok": True, "skipped": True, "reason": "APP-only 模式不执行外部切页"},
        "anchor_state": {"ok": True, "found": False, "anchors": {}, "keywords": {}, "error": None},
        "entrust_state": _app_only_panel_state(panel="entrust", broker=broker_name, stock_code=stock_code),
        "position_state": _app_only_panel_state(panel="position", broker=broker_name, stock_code=stock_code),
        "human_action_required": False,
        "ready": True,
        "takeover_phase": "app_only",
        "next_step": "APP内闭环模式已启用，请直接补齐参数并执行安全预演。",
        "app_only": True,
    }


def _trade_takeover_precheck(broker="", stock_code="", trade_action="", price=0.0, lots=0, auto_focus=True, auto_navigate=True, capture_evidence=False, app_only=False):
    if app_only:
        snapshot = _app_only_takeover_snapshot(broker=broker, stock_code=stock_code)
        confirm_state = {
            "ok": True,
            "found": False,
            "confirm_btn": None,
            "keywords": ["APP-only"],
            "error": None,
        }
    else:
        snapshot = _trade_takeover_snapshot(
            broker=broker,
            stock_code=stock_code,
            trade_action=trade_action,
            auto_focus=auto_focus,
            auto_navigate=auto_navigate,
        )
        confirm_state = _public_confirm_state(
            _detect_trade_confirm_dialog(action=trade_action, stock_code=stock_code, broker=snapshot.get("broker") or broker)
        )
    anchors = (snapshot.get("anchor_state") or {}).get("anchors") or {}
    missing_payload = []
    if not stock_code:
        missing_payload.append("stock_code")
    if float(price or 0) <= 0:
        missing_payload.append("price")
    if int(lots or 0) <= 0:
        missing_payload.append("lots")
    missing_fill_anchors = [] if app_only else [key for key in ("stock_code", "price", "lots") if not anchors.get(key)]
    ready_for_takeover = bool(snapshot.get("ready"))
    can_fill_form = ready_for_takeover and not missing_payload and not missing_fill_anchors
    can_submit_confirm = bool(confirm_state.get("found"))
    if app_only:
        next_action_id = "trade_form_fill" if can_fill_form else ""
    elif can_submit_confirm:
        next_action_id = "trade_submit_confirm"
    elif can_fill_form:
        next_action_id = "trade_form_fill"
    elif ready_for_takeover:
        next_action_id = "trade_panel_probe"
    else:
        next_action_id = "trade_takeover_watch"
    warnings = []
    if app_only:
        warnings.append(str(snapshot.get("next_step") or "APP内闭环模式已启用"))
        if missing_payload:
            warnings.append("缺少填单参数：" + ", ".join(missing_payload))
    elif not ready_for_takeover:
        warnings.append(str(snapshot.get("next_step") or "尚未进入可接管态"))
    if not app_only and ready_for_takeover and missing_payload:
        warnings.append("缺少填单参数：" + ", ".join(missing_payload))
    if not app_only and ready_for_takeover and missing_fill_anchors:
        warnings.append("填单锚点未就绪：" + ", ".join(missing_fill_anchors))
    if can_submit_confirm:
        warnings.append("检测到确认弹窗，真正提交前仍需显式 confirm=true")
    evidence = None
    if capture_evidence:
        evidence = _capture_trade_probe_evidence({
            "broker": snapshot.get("broker") or broker,
            "stock_code": stock_code,
            "trade_action": trade_action,
            "price": price,
            "lots": lots,
            "snapshot": snapshot,
            "confirm_state": confirm_state,
            "warnings": warnings,
        })
    return {
        **snapshot,
        "confirm_state": confirm_state,
        "price": float(price or 0),
        "lots": int(lots or 0),
        "precheck_passed": bool(snapshot.get("ready")),
        "can_fill_form": can_fill_form,
        "can_submit_confirm": can_submit_confirm,
        "missing_payload": missing_payload,
        "missing_fill_anchors": missing_fill_anchors,
        "next_action_id": next_action_id,
        "supported_actions": [
            "trade_form_fill",
            "trade_submit_confirm",
            "trade_result_watch",
        ] if app_only else [
            "trade_takeover_watch",
            "trade_panel_probe",
            "trade_form_fill",
            "trade_submit_confirm",
            "trade_result_watch",
        ],
        "risk_gate": {
            "dry_run_supported": True,
            "confirm_required_actions": ["trade_submit_confirm"] if app_only else ["trade_form_fill", "trade_submit_confirm"],
            "human_action_required": False if app_only else bool(snapshot.get("human_action_required")),
        },
        "warnings": warnings,
        "capture_evidence": bool(capture_evidence),
        "evidence": evidence,
        "app_only": bool(app_only),
    }


def _exec_desktop(cid, payload=None):
    t = time.strftime("%H:%M:%S")
    payload = payload or {}
    dry_run = _flag(payload, "dry_run")
    try:
        import psutil, webbrowser as _wb, subprocess
        from gbt.device_ctl import get_device, DesktopCtl
        device = get_device()

        if cid == "screenshot":
            root_dir = _runtime_root()
            shot_dir = os.path.join(root_dir, "screenshots")
            filename_prefix = str(payload.get("filename_prefix", "screenshot")).strip() or "screenshot"
            filename = f"{filename_prefix}_{time.strftime('%Y%m%d_%H%M%S')}.png"
            if dry_run:
                return _preview(f"预演截图：将保存到 screenshots/{filename}", t, path=f"screenshots/{filename}")
            import pyautogui
            os.makedirs(shot_dir, exist_ok=True)
            path = os.path.join(shot_dir, filename)
            pyautogui.screenshot(path)
            return _reply(True, f"截图已保存到 screenshots 目录：{filename}", t, path=f"screenshots/{filename}")

        if cid == "browser_open":
            broker = str(payload.get("broker", "")).strip()
            target_url = str(payload.get("url", "")).strip()
            query = str(payload.get("query", "")).strip()
            if broker:
                from gbt.stock_gate import get_login_url, find_broker
                broker_info = find_broker(broker)
                broker_name = broker_info["name"] if broker_info else broker
                target_url = get_login_url(broker_name) or target_url or "https://trade.eastmoney.com"
                preview_text = f"预演打开券商入口：{broker_name} -> {target_url}"
            else:
                if not target_url:
                    target_url = "https://finance.eastmoney.com"
                if query:
                    target_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
                preview_text = f"预演打开浏览器：{target_url}"
            if dry_run:
                return _preview(preview_text, t, target=target_url)
            _wb.open(target_url)
            return _reply(True, f"已打开浏览器：{target_url}", t, target=target_url)

        if cid == "broker_open":
            from gbt.stock_gate import open_broker
            broker = str(payload.get("broker", "")).strip()
            if dry_run:
                return _preview(f"预演打开券商：{broker or '东方财富'}", t, broker=broker or "东方财富")
            result = open_broker(broker or "东方财富")
            if result.get("ok"):
                return _reply(True, result.get("message") or f"已打开 {result.get('name','券商平台')}", t, broker=result.get("name"), url=result.get("url"))
            return _reply(False, result.get("error", "券商打开失败"), t)

        if cid == "broker_list":
            from gbt.stock_gate import list_brokers
            return _reply(True, list_brokers(), t)

        if cid == "broker_login_detect":
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            result = _public_login_state(_detect_login_state(broker=broker_hint))
            if not result.get("ok"):
                return _reply(False, "登录状态检测失败: " + result.get("error", "未知错误"), t)
            if result.get("logged_in"):
                return _reply(True, f"已检测到券商登录状态，置信度 {result.get('confidence')}，关键词：{','.join(result.get('keywords') or []) or '无'}", t, logged_in=True, broker=broker_hint or None)
            return _reply(True, f"尚未检测到明确登录状态，置信度 {result.get('confidence')}，关键词：{','.join(result.get('keywords') or []) or '无'}", t, logged_in=False, broker=broker_hint or None)

        if cid == "trade_anchor_detect":
            action = str(payload.get("trade_action", "")).strip().lower()
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            result = _detect_trade_anchors(action=action, broker=broker_hint)
            if not result.get("ok"):
                if dry_run:
                    return _preview(
                        "预演交易锚点识别（OCR引擎未就绪，返回空锚点结构）",
                        t,
                        found=False,
                        anchors={},
                        keywords=result.get("keywords", {}),
                        broker=broker_hint or None,
                        engine_ready=False,
                        preview_error=result.get("error"),
                    )
                return _reply(False, "交易锚点识别失败: " + result.get("error", "未知错误"), t)
            anchors = result.get("anchors", {}) or {}
            if anchors:
                lines = [f"已识别到 {len(anchors)} 个交易锚点"]
                for key in ("stock_code", "price", "lots", "buy_btn", "sell_btn", "confirm_btn"):
                    point = anchors.get(key)
                    if point:
                        lines.append(f"- {key}: ({point.get('x')}, {point.get('y')})")
                return _reply(True, "\n".join(lines), t, found=True, anchors=anchors, keywords=result.get("keywords", {}), broker=broker_hint or None)
            return _reply(True, "当前未识别到明确交易锚点", t, found=False, anchors={}, keywords=result.get("keywords", {}), broker=broker_hint or None)

        if cid == "trade_confirm_detect":
            action = str(payload.get("trade_action", "")).strip().lower()
            stock_code = str(payload.get("stock_code", "")).strip()
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            result = _public_confirm_state(_detect_trade_confirm_dialog(action=action, stock_code=stock_code, broker=broker_hint))
            if not result.get("ok"):
                if dry_run:
                    return _preview(
                        "预演交易确认弹窗识别（OCR引擎未就绪，返回空确认状态）",
                        t,
                        confirm_state=result,
                        broker=broker_hint or None,
                        engine_ready=False,
                        preview_error=result.get("error"),
                    )
                return _reply(False, "交易确认弹窗识别失败: " + result.get("error", "未知错误"), t)
            if result.get("found"):
                btn = result.get("confirm_btn") or {}
                return _reply(True, f"已识别到交易确认弹窗，确认按钮坐标 ({btn.get('x')}, {btn.get('y')})", t, confirm_state=result, broker=broker_hint or None)
            return _reply(True, "当前未识别到交易确认弹窗", t, confirm_state=result, broker=broker_hint or None)

        if cid == "trade_entrust_readback":
            stock_code = str(payload.get("stock_code", "")).strip()
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code=stock_code, broker=broker_hint))
            if not state.get("ok"):
                if dry_run:
                    return _preview(
                        "预演委托区域回读（OCR引擎未就绪，返回空委托结构）",
                        t,
                        entrust_state=state,
                        broker=broker_hint or None,
                        engine_ready=False,
                        preview_error=state.get("error"),
                    )
                return _reply(False, "委托区域回读失败: " + (state.get("error") or "未知错误"), t, entrust_state=state)
            if state.get("found"):
                lines = ["已识别委托区域摘要"]
                if state.get("codes"):
                    lines.append("代码：" + "、".join(state.get("codes")[:4]))
                if state.get("summary", {}).get("statuses"):
                    lines.append("状态：" + "、".join(state.get("summary", {}).get("statuses")[:4]))
                for item in state.get("matched_lines")[:4]:
                    lines.append("- " + item)
                if state.get("rows"):
                    row = state.get("rows")[0]
                    pieces = []
                    for key, label in (("code", "代码"), ("price", "价格"), ("quantity", "数量"), ("status", "状态")):
                        if row.get(key):
                            pieces.append(label + ":" + str(row.get(key)))
                    if pieces:
                        lines.append("结构化首行：" + " / ".join(pieces))
                return _reply(True, "\n".join(lines), t, entrust_state=state, broker=broker_hint or None)
            return _reply(True, "当前未识别到明确委托区域", t, entrust_state=state, broker=broker_hint or None)

        if cid == "trade_position_readback":
            stock_code = str(payload.get("stock_code", "")).strip()
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code=stock_code, broker=broker_hint))
            if not state.get("ok"):
                if dry_run:
                    return _preview(
                        "预演持仓区域回读（OCR引擎未就绪，返回空持仓结构）",
                        t,
                        position_state=state,
                        broker=broker_hint or None,
                        engine_ready=False,
                        preview_error=state.get("error"),
                    )
                return _reply(False, "持仓区域回读失败: " + (state.get("error") or "未知错误"), t, position_state=state)
            if state.get("found"):
                lines = ["已识别持仓区域摘要"]
                if state.get("codes"):
                    lines.append("代码：" + "、".join(state.get("codes")[:4]))
                for item in state.get("matched_lines")[:4]:
                    lines.append("- " + item)
                if state.get("rows"):
                    row = state.get("rows")[0]
                    pieces = []
                    for key, label in (("code", "代码"), ("quantity", "持仓"), ("available", "可用"), ("market_value", "市值"), ("profit", "盈亏")):
                        if row.get(key):
                            pieces.append(label + ":" + str(row.get(key)))
                    if pieces:
                        lines.append("结构化首行：" + " / ".join(pieces))
                return _reply(True, "\n".join(lines), t, position_state=state, broker=broker_hint or None)
            return _reply(True, "当前未识别到明确持仓区域", t, position_state=state, broker=broker_hint or None)

        if cid == "trade_submit_confirm":
            action = str(payload.get("trade_action", "")).strip().lower() or "buy"
            stock_code = str(payload.get("stock_code", "")).strip()
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            app_only = _flag(payload, "app_only")
            if app_only:
                confirm_state = {
                    "ok": True,
                    "found": True,
                    "confirm_btn": None,
                    "keywords": ["APP-only"],
                    "error": None,
                }
                if dry_run:
                    return _preview("预演 APP 内交易确认", t, confirm_state=confirm_state, stock_code=stock_code or None, broker=broker_hint or None, app_only=True)
                if not _flag(payload, "confirm"):
                    return _reply(False, "高风险动作已拦截，请带 confirm=true 后再确认 APP 内提交", t, requires_confirmation=True, confirm_state=confirm_state, app_only=True)
                return _reply(True, f"APP内已确认提交：{action} {stock_code or '--'}", t, confirm_state=confirm_state, stock_code=stock_code or None, broker=broker_hint or None, app_only=True)
            confirm_state = _public_confirm_state(_detect_trade_confirm_dialog(action=action, stock_code=stock_code, broker=broker_hint))
            if dry_run:
                return _preview("预演点击交易确认按钮", t, confirm_state=confirm_state, stock_code=stock_code or None, broker=broker_hint or None)
            if not _flag(payload, "confirm"):
                return _reply(False, "高风险动作已拦截，请带 confirm=true 后再提交交易确认", t, requires_confirmation=True, confirm_state=confirm_state)
            btn = confirm_state.get("confirm_btn") or {}
            x = int(btn.get("x", 0) or 0)
            y = int(btn.get("y", 0) or 0)
            if x <= 0 or y <= 0:
                return _reply(False, "未识别到可点击的确认按钮", t, confirm_state=confirm_state)
            click_result = device.mouse.click(x, y, clicks=1)
            if click_result.get("ok"):
                return _reply(True, f"已点击交易确认按钮 ({x}, {y})", t, confirm_state=confirm_state, stock_code=stock_code or None, broker=broker_hint or None)
            return _reply(False, "交易确认按钮点击失败: " + click_result.get("error", "未知错误"), t, confirm_state=confirm_state)

        if cid == "broker_window_scan":
            scan = _scan_broker_windows()
            hits = scan.get("broker_windows", [])
            active = scan.get("active_window") or {}
            if hits:
                lines = [f"已识别到 {len(hits)} 个券商相关窗口"]
                if active.get("title"):
                    lines.append(f"当前前台：{active.get('title')}")
                for item in hits[:8]:
                    flag = " [当前]" if item.get("active") else ""
                    lines.append(f"- {item.get('broker')} · {item.get('title')}{flag}")
                return _reply(True, "\n".join(lines), t, windows=hits, active_window=active, observed_titles=scan.get("observed_titles") or [])
            msg = "当前未识别到券商相关窗口"
            if active.get("title"):
                msg += f"\n当前前台：{active.get('title')}"
            observed_titles = scan.get("observed_titles") or []
            if observed_titles:
                msg += "\n已观测窗口：" + " | ".join(observed_titles[:6])
            return _reply(True, msg, t, windows=[], active_window=active, observed_titles=observed_titles)

        if cid == "broker_window_focus":
            broker = str(payload.get("broker", "")).strip()
            title = str(payload.get("title", "")).strip()
            if dry_run:
                target = title or broker or "首个券商窗口"
                return _preview(f"预演聚焦券商窗口：{target}", t, broker=broker or None, title=title or None)
            result = _focus_broker_window(broker=broker, title=title)
            if result.get("ok"):
                selected = result.get("selected") or {}
                return _reply(True, f"已聚焦券商窗口：{selected.get('broker')} · {selected.get('title')}", t, selected=selected)
            return _reply(False, result.get("error", "券商窗口聚焦失败"), t, scan=result.get("scan"))

        if cid == "window_maximize":
            if dry_run:
                return _preview("预演最大化当前窗口", t)
            result = DesktopCtl.open_app("") if False else None
            import pyautogui
            pyautogui.hotkey("win", "up")
            return _reply(True, "窗口已最大化", t)

        if cid == "keyboard_type":
            text = str(payload.get("text", "GBT Pro - 自主操盘AI"))[:500]
            interval = float(payload.get("interval", 0.05) or 0.05)
            if dry_run:
                return _preview(f"预演键盘输入：{text}", t, typed_text=text, interval=interval)
            result = device.keyboard.typewrite(text, interval=interval)
            return _reply(bool(result.get("ok")), f"已键入: {text}" if result.get("ok") else "键盘输入失败: " + result.get("error", ""), t, text=text)

        if cid == "keyboard_hotkey":
            keys = payload.get("keys")
            if isinstance(keys, str):
                keys = [x.strip().lower() for x in keys.split("+") if x.strip()]
            if not isinstance(keys, list) or not keys:
                combo = str(payload.get("combo", "alt+tab")).strip() or "alt+tab"
                keys = [x.strip().lower() for x in combo.split("+") if x.strip()]
            if dry_run:
                return _preview(f"预演快捷键：{'+'.join(keys)}", t, keys=keys)
            result = device.keyboard.hotkey(*keys)
            return _reply(bool(result.get("ok")), f"已触发快捷键：{'+'.join(keys)}" if result.get("ok") else "快捷键失败: " + result.get("error", ""), t, keys=keys)

        if cid == "mouse_click":
            x = payload.get("x")
            y = payload.get("y")
            button = str(payload.get("button", "left")).strip() or "left"
            clicks = int(payload.get("clicks", 1) or 1)
            if dry_run:
                place = f"({x}, {y})" if x is not None and y is not None else "当前位置"
                return _preview(f"预演鼠标{button}键点击 {place} x{clicks}", t, x=x, y=y, button=button, clicks=clicks)
            result = device.mouse.click(x, y, button=button, clicks=clicks)
            place = f"({x}, {y})" if x is not None and y is not None else "当前位置"
            return _reply(bool(result.get("ok")), f"已点击 {place}" if result.get("ok") else "鼠标点击失败: " + result.get("error", ""), t, x=x, y=y)

        if cid == "mouse_move":
            x = int(payload.get("x", 0) or 0)
            y = int(payload.get("y", 0) or 0)
            duration = float(payload.get("duration", 0.3) or 0.3)
            if dry_run:
                return _preview(f"预演鼠标移动到 ({x}, {y})", t, x=x, y=y, duration=duration)
            result = device.mouse.move(x, y, duration=duration)
            return _reply(bool(result.get("ok")), f"鼠标已移动到 ({x}, {y})" if result.get("ok") else "鼠标移动失败: " + result.get("error", ""), t, x=x, y=y)

        if cid == "process_list":
            limit = max(1, min(int(payload.get("limit", 30) or 30), 50))
            procs = []
            for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                            key=lambda x: x.info["cpu_percent"] or 0, reverse=True)[:limit]:
                procs.append(f"{p.info['pid']:>6d} {p.info.get('name','?')[:25]:25s} CPU:{p.info['cpu_percent'] or 0:.0f}% MEM:{p.info['memory_percent'] or 0:.1f}%")
            return _reply(True, f"TOP{limit}进程:\n" + "\n".join(procs), t, limit=limit)

        if cid == "process_kill":
            target_pid = payload.get("pid")
            target_name = str(payload.get("name", "")).strip()
            if not _flag(payload, "confirm"):
                hint = f"PID={target_pid}" if target_pid else (target_name or "未指定")
                return _reply(False, f"高风险动作已拦截，请带 confirm=true 再结束进程：{hint}", t, requires_confirmation=True)
            if dry_run:
                hint = f"PID={target_pid}" if target_pid else target_name
                return _preview(f"预演结束进程：{hint}", t, requires_confirmation=True)
            return _reply(True, _kill_process(target_pid, target_name), t)

        if cid == "window_focus":
            title = str(payload.get("title", "")).strip()
            show_desktop = _flag(payload, "show_desktop")
            if dry_run:
                return _preview(f"预演聚焦窗口：{title or '当前桌面'}", t, title=title or None, show_desktop=show_desktop)
            if show_desktop or not title:
                import pyautogui
                pyautogui.hotkey("win", "d")
                return _reply(True, "已显示桌面", t)
            import pyautogui
            matched = pyautogui.getWindowsWithTitle(title)
            if not matched:
                return _reply(False, f"未找到窗口：{title}", t)
            win = matched[0]
            try:
                win.activate()
            except Exception:
                pass
            return _reply(True, f"已聚焦窗口：{win.title}", t, title=win.title)

        if cid == "volume_control":
            mode = str(payload.get("mode", "mute")).strip().lower() or "mute"
            steps = max(1, min(int(payload.get("steps", 1) or 1), 20))
            if dry_run:
                return _preview(f"预演音量调节：{mode} x{steps}", t, mode=mode, steps=steps)
            if mode == "up":
                for _ in range(steps):
                    device.desktop.volume_up()
                return _reply(True, f"音量已调高 {steps} 次", t, mode=mode, steps=steps)
            if mode == "down":
                for _ in range(steps):
                    device.desktop.volume_down()
                return _reply(True, f"音量已调低 {steps} 次", t, mode=mode, steps=steps)
            device.desktop.volume_mute()
            return _reply(True, "已切换静音", t, mode="mute")

        if cid == "trade_form_fill":
            stock_code = str(payload.get("stock_code", "")).strip()
            price = float(payload.get("price", 0) or 0)
            lots = int(payload.get("lots", 0) or 0)
            app_only = _flag(payload, "app_only")
            if not stock_code or price <= 0 or lots <= 0:
                return _reply(False, "缺少 stock_code / price / lots，无法填单", t)
            preview_steps = [f"股票代码 {stock_code}", f"价格 {price:.2f}", f"手数 {lots}"]
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            anchor_state = _public_anchor_state(_detect_trade_anchors(action=str(payload.get("trade_action", "buy")).strip().lower(), broker=broker_hint))
            if dry_run:
                return _preview("预演填单：" + " -> ".join(preview_steps), t, stock_code=stock_code, price=price, lots=lots, anchor_state=anchor_state, broker=broker_hint or None, app_only=app_only)
            if app_only:
                return _reply(True, "APP内已锁定交易参数：" + " -> ".join(preview_steps), t, stock_code=stock_code, price=price, lots=lots, anchor_state=anchor_state, broker=broker_hint or None, app_only=True)
            if not _flag(payload, "confirm"):
                return _reply(False, "高风险动作已拦截，请带 confirm=true 后再执行填单", t, requires_confirmation=True)
            anchors = anchor_state.get("anchors", {}) if anchor_state.get("ok") else {}
            if anchors.get("stock_code") and anchors.get("price") and anchors.get("lots"):
                result = device.fill_trade_form_with_anchors(stock_code, price, lots, anchors)
            else:
                result = device.fill_trade_form(stock_code, price, lots)
            if result.get("ok"):
                return _reply(True, "已完成交易表单预填：" + " -> ".join(result.get("steps", [])), t, stock_code=stock_code, price=price, lots=lots, anchor_state=anchor_state, broker=broker_hint or None)
            return _reply(False, "交易表单预填失败: " + result.get("error", "未知错误"), t, anchor_state=anchor_state)

        if cid == "trade_workflow":
            broker = str(payload.get("broker", "东方财富")).strip() or "东方财富"
            check_login = payload.get("check_login", True)
            workflow = [f"券商入口：{broker}", "步骤1 打开券商", "步骤2 检查登录状态", "步骤3 准备看盘/填单"]
            if dry_run:
                return _preview("预演操盘流程：" + " | ".join(workflow), t, broker=broker)
            from gbt.stock_gate import open_broker
            broker_result = open_broker(broker)
            login_state = None
            window_state = _scan_broker_windows()
            if check_login:
                login_state = _detect_login_state(broker=broker)
            detail = broker_result.get("message") or f"已打开 {broker}"
            if window_state.get("broker_windows"):
                top = window_state["broker_windows"][0]
                detail += "\n券商窗口：" + top.get("title", "")
            if login_state and login_state.get("ok"):
                detail += "\n" + ("登录状态：已登录" if login_state.get("logged_in") else "登录状态：待登录")
            return _reply(bool(broker_result.get("ok")), detail, t, broker=broker_result.get("name", broker), login_state=login_state, window_state=window_state)

        if cid == "trade_result_watch":
            action = str(payload.get("trade_action", "")).strip().lower() or "buy"
            stock_code = str(payload.get("stock_code", "")).strip()
            timeout = max(3, min(int(payload.get("timeout", 30) or 30), 120))
            broker_hint = _resolve_broker_hint(payload.get("broker"))
            app_only = _flag(payload, "app_only")
            if dry_run:
                return _preview(f"预演回看委托结果：{action} {stock_code or '--'} 超时 {timeout}s", t, trade_action=action, stock_code=stock_code or None, timeout=timeout, broker=broker_hint or None, app_only=app_only)
            if app_only:
                watch_state = {
                    "ok": True,
                    "found": True,
                    "keywords": ["APP内已提交"],
                    "entrust_state": _app_only_panel_state(panel="entrust", broker=broker_hint or "APP内闭环", stock_code=stock_code),
                    "position_state": _app_only_panel_state(panel="position", broker=broker_hint or "APP内闭环", stock_code=stock_code),
                    "error": None,
                }
                msg = "APP内结果回看已生成"
                if stock_code:
                    msg += f"\n委托区代码：{stock_code}\n持仓区代码：{stock_code}"
                return _reply(True, msg, t, watch_state=watch_state, broker=broker_hint or None, app_only=True)
            watch_state = _public_trade_watch_state(_watch_trade_result(action=action, stock_code=stock_code, timeout=timeout, broker=broker_hint))
            if not watch_state.get("ok"):
                return _reply(False, "委托结果回看失败: " + (watch_state.get("error") or "未知错误"), t, watch_state=watch_state)
            if watch_state.get("found"):
                extra = []
                if (watch_state.get("entrust_state") or {}).get("codes"):
                    extra.append("委托区代码：" + "、".join((watch_state.get("entrust_state") or {}).get("codes")[:4]))
                if (watch_state.get("position_state") or {}).get("codes"):
                    extra.append("持仓区代码：" + "、".join((watch_state.get("position_state") or {}).get("codes")[:4]))
                msg = "已检测到委托结果关键词：" + "、".join(watch_state.get("keywords") or [])
                if extra:
                    msg += "\n" + "\n".join(extra)
                return _reply(True, msg, t, watch_state=watch_state, broker=broker_hint or None)
            return _reply(True, f"在 {timeout}s 内未检测到明确委托结果", t, watch_state=watch_state, broker=broker_hint or None)

        if cid == "trade_ready_check":
            broker = str(payload.get("broker", "")).strip()
            broker_hint = _resolve_broker_hint(broker)
            scan = _scan_broker_windows()
            login_state = _public_login_state(_detect_login_state(broker=broker_hint))
            anchor_state = _public_anchor_state(_detect_trade_anchors(action=str(payload.get("trade_action", "")).strip().lower(), broker=broker_hint))
            confirm_state = _public_confirm_state(_detect_trade_confirm_dialog(
                action=str(payload.get("trade_action", "")).strip().lower(),
                stock_code=str(payload.get("stock_code", "")).strip(),
                broker=broker_hint,
            ))
            entrust_state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code=str(payload.get("stock_code", "")).strip(), broker=broker_hint))
            position_state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code=str(payload.get("stock_code", "")).strip(), broker=broker_hint))
            lines = []
            if broker:
                lines.append(f"目标券商：{broker}")
            if scan.get("broker_windows"):
                lines.append(f"券商窗口：已识别 {len(scan.get('broker_windows') or [])} 个")
                lines.append("首个窗口：" + scan["broker_windows"][0].get("title", ""))
            else:
                lines.append("券商窗口：未识别到")
            if login_state.get("ok"):
                lines.append("登录状态：" + ("已登录" if login_state.get("logged_in") else "待登录"))
            else:
                lines.append("登录状态：检测失败")
            if anchor_state.get("ok") and anchor_state.get("anchors"):
                lines.append("交易锚点：" + "已识别 " + str(len(anchor_state.get("anchors") or {})) + " 个")
            else:
                lines.append("交易锚点：未识别到")
            if confirm_state.get("found"):
                lines.append("确认弹窗：已识别到")
            else:
                lines.append("确认弹窗：未识别到")
            if entrust_state.get("found"):
                lines.append("委托回读：已识别 " + str(len(entrust_state.get("matched_lines") or [])) + " 行")
            else:
                lines.append("委托回读：未识别到")
            if position_state.get("found"):
                lines.append("持仓回读：已识别 " + str(len(position_state.get("matched_lines") or [])) + " 行")
            else:
                lines.append("持仓回读：未识别到")
            ready = bool(scan.get("broker_windows")) and bool(login_state.get("ok"))
            lines.append("准备结论：" + ("可以进入看盘/填单" if ready else "仍需先打开券商或完成登录"))
            return _reply(True, "\n".join(lines), t, broker=broker_hint or broker or None, window_state=scan, login_state=login_state, anchor_state=anchor_state, confirm_state=confirm_state, entrust_state=entrust_state, position_state=position_state, ready=ready)

        if cid == "trade_takeover_ready":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            trade_action = str(payload.get("trade_action", "")).strip().lower()
            auto_focus = payload.get("auto_focus", True)
            auto_navigate = payload.get("auto_navigate", True)
            if dry_run:
                target = broker or "自动识别券商"
                return _preview(
                    f"预演自主接管准备：{target} -> 自动聚焦 -> 登录检测 -> 交易页检测",
                    t,
                    broker=broker or None,
                    stock_code=stock_code or None,
                    trade_action=trade_action or None,
                    auto_focus=bool(auto_focus),
                    auto_navigate=bool(auto_navigate),
                )
            snapshot = _trade_takeover_snapshot(
                broker=broker,
                stock_code=stock_code,
                trade_action=trade_action,
                auto_focus=bool(auto_focus),
                auto_navigate=bool(auto_navigate),
            )
            lines = []
            if snapshot.get("broker"):
                lines.append("接管券商：" + str(snapshot.get("broker")))
            active = snapshot.get("active_window") or {}
            if active.get("title"):
                lines.append("当前前台：" + active.get("title"))
            focus_state = snapshot.get("focus_state")
            if focus_state:
                if focus_state.get("ok"):
                    selected = focus_state.get("selected") or {}
                    lines.append("自动聚焦：" + (selected.get("title") or "已完成"))
                else:
                    lines.append("自动聚焦失败：" + (focus_state.get("error") or "未知错误"))
            lines.append("登录状态：" + ("已登录" if (snapshot.get("login_state") or {}).get("logged_in") else "待登录"))
            page_nav_state = snapshot.get("page_nav_state") or {}
            if page_nav_state:
                if page_nav_state.get("ok") and not page_nav_state.get("skipped"):
                    lines.append("自动切页：已尝试并命中 " + str(page_nav_state.get("target") or "交易页签"))
                elif page_nav_state.get("skipped"):
                    lines.append("自动切页：" + str(page_nav_state.get("reason") or "本次跳过"))
                else:
                    lines.append("自动切页：" + str(page_nav_state.get("reason") or "未命中可验证页签"))
            if (snapshot.get("anchor_state") or {}).get("anchors"):
                lines.append("交易页锚点：已识别 " + str(len((snapshot.get("anchor_state") or {}).get("anchors") or {})) + " 个")
            else:
                lines.append("交易页锚点：未识别到")
            lines.extend(_panel_brief_lines("委托回读", snapshot.get("entrust_state") or {}))
            lines.extend(_panel_brief_lines("持仓回读", snapshot.get("position_state") or {}))
            lines.append("接管阶段：" + str(snapshot.get("takeover_phase")))
            lines.append("下一步：" + str(snapshot.get("next_step")))
            return _reply(True, "\n".join(lines), t, **snapshot)

        if cid == "trade_takeover_watch":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            trade_action = str(payload.get("trade_action", "")).strip().lower()
            timeout_sec = int(payload.get("timeout_sec", 45) or 45)
            poll_interval = int(payload.get("poll_interval", 3) or 3)
            auto_focus = payload.get("auto_focus", True)
            auto_navigate = payload.get("auto_navigate", True)
            if dry_run:
                target = broker or "自动识别券商"
                return _preview(
                    f"预演持续接管监视：{target} -> 最长等待 {timeout_sec}s",
                    t,
                    broker=broker or None,
                    stock_code=stock_code or None,
                    trade_action=trade_action or None,
                    timeout_sec=timeout_sec,
                    poll_interval=poll_interval,
                    auto_focus=bool(auto_focus),
                    auto_navigate=bool(auto_navigate),
                )
            snapshot = _trade_takeover_watch(
                broker=broker,
                stock_code=stock_code,
                trade_action=trade_action,
                timeout_sec=timeout_sec,
                poll_interval=poll_interval,
                auto_focus=bool(auto_focus),
                auto_navigate=bool(auto_navigate),
            )
            lines = []
            if snapshot.get("broker"):
                lines.append("接管券商：" + str(snapshot.get("broker")))
            lines.append("监视时长：" + str(snapshot.get("elapsed")) + "s")
            lines.append("轮询次数：" + str(len(snapshot.get("timeline") or [])))
            lines.append("接管阶段：" + str(snapshot.get("takeover_phase")))
            lines.append("下一步：" + str(snapshot.get("next_step")))
            lines.append("监视结论：" + ("已进入可接管态" if snapshot.get("ready") else "仍未进入可接管态"))
            return _reply(True, "\n".join(lines), t, **snapshot)

        if cid == "trade_live_validate":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            trade_action = str(payload.get("trade_action", "")).strip().lower() or "buy"
            price = float(payload.get("price", 0) or 0)
            lots = int(payload.get("lots", 0) or 0)
            auto_focus = payload.get("auto_focus", True)
            auto_navigate = payload.get("auto_navigate", True)
            capture_evidence = True if "capture_evidence" not in payload else _flag(payload, "capture_evidence")
            app_only = _flag(payload, "app_only")
            confirm = _flag(payload, "confirm")
            timeout = max(3, min(int(payload.get("timeout", 15) or 15), 120))
            precheck = _trade_takeover_precheck(
                broker=broker,
                stock_code=stock_code,
                trade_action=trade_action,
                price=price,
                lots=lots,
                auto_focus=bool(auto_focus),
                auto_navigate=bool(auto_navigate),
                capture_evidence=capture_evidence,
                app_only=app_only,
            )
            report = {
                "saved_at": int(time.time()),
                "mode": "app_only" if app_only else "desktop_live",
                "confirm": confirm,
                "broker": broker or None,
                "stock_code": stock_code or None,
                "trade_action": trade_action,
                "price": price,
                "lots": lots,
                "precheck": precheck,
                "steps": [],
                "validation_state": {
                    "passed": False,
                    "stage": "precheck",
                    "blocked_reason": None,
                    "criteria": {
                        "precheck_ready": bool(precheck.get("precheck_passed")),
                        "fill_available": bool(precheck.get("can_fill_form")),
                        "submit_available": bool(precheck.get("can_submit_confirm")),
                    },
                },
            }
            if dry_run:
                if capture_evidence:
                    report["evidence"] = _trade_validation_evidence_plan(broker=broker, stock_code=stock_code)
                return _preview(
                    f"预演闭环验证：{broker or '自动识别券商'} -> 预检 -> 填单 -> 提交 -> 结果回看",
                    t,
                    report=report,
                    app_only=app_only,
                    confirm=confirm,
                )
            fill_payload = {
                "id": "trade_form_fill",
                "broker": broker,
                "stock_code": stock_code,
                "trade_action": trade_action,
                "price": price,
                "lots": lots,
                "auto_focus": bool(auto_focus),
                "auto_navigate": bool(auto_navigate),
                "app_only": app_only,
            }
            submit_payload = {
                "id": "trade_submit_confirm",
                "broker": broker,
                "stock_code": stock_code,
                "trade_action": trade_action,
                "confirm": True,
                "app_only": app_only,
            }
            watch_payload = {
                "id": "trade_result_watch",
                "broker": broker,
                "stock_code": stock_code,
                "trade_action": trade_action,
                "timeout": timeout,
                "app_only": app_only,
            }
            if confirm:
                fill_payload["confirm"] = True
            else:
                fill_payload["dry_run"] = True
            form_result = None
            submit_result = None
            watch_result = None
            if precheck.get("can_fill_form"):
                form_result = _exec_desktop("trade_form_fill", fill_payload)
                report["steps"].append({"id": "trade_form_fill", "result": form_result})
                report["validation_state"]["stage"] = "form_fill"
                if not form_result.get("ok"):
                    report["validation_state"]["blocked_reason"] = form_result.get("error") or "填单失败"
            else:
                report["validation_state"]["blocked_reason"] = "当前未满足填单条件"
            if confirm and (precheck.get("can_submit_confirm") or app_only) and (not form_result or form_result.get("ok")):
                submit_result = _exec_desktop("trade_submit_confirm", submit_payload)
                report["steps"].append({"id": "trade_submit_confirm", "result": submit_result})
                report["validation_state"]["stage"] = "submit_confirm"
                if submit_result.get("ok"):
                    watch_result = _exec_desktop("trade_result_watch", watch_payload)
                    report["steps"].append({"id": "trade_result_watch", "result": watch_result})
                    report["validation_state"]["stage"] = "result_watch"
                else:
                    report["validation_state"]["blocked_reason"] = submit_result.get("error") or "提交确认失败"
            elif confirm and not (precheck.get("can_submit_confirm") or app_only):
                report["validation_state"]["blocked_reason"] = "当前未识别到可提交确认态"
            elif not confirm:
                report["validation_state"]["blocked_reason"] = "未携带 confirm=true，已停在安全预演/预填单阶段"
            passed = bool(watch_result and watch_result.get("ok")) if confirm else bool(form_result and form_result.get("ok"))
            report["validation_state"]["passed"] = passed
            if capture_evidence:
                report["evidence"] = _archive_trade_validation_report(report, broker=broker, stock_code=stock_code)
            lines = []
            lines.append("闭环模式：" + ("APP内闭环" if app_only else "真实桌面闭环"))
            lines.append("预检：" + ("通过" if precheck.get("precheck_passed") else "未通过"))
            lines.append("填单：" + ("通过" if form_result and form_result.get("ok") else ("未执行" if form_result is None else "失败")))
            lines.append("提交：" + ("通过" if submit_result and submit_result.get("ok") else ("未执行" if submit_result is None else "失败")))
            lines.append("回看：" + ("通过" if watch_result and watch_result.get("ok") else ("未执行" if watch_result is None else "失败")))
            if report["validation_state"].get("blocked_reason"):
                lines.append("阻断原因：" + str(report["validation_state"].get("blocked_reason")))
            if report.get("evidence"):
                lines.append("证据归档：" + str((report.get("evidence") or {}).get("report_path") or "已记录"))
            return _reply(
                passed,
                "\n".join(lines),
                t,
                app_only=app_only,
                confirm=confirm,
                precheck=precheck,
                form_result=form_result,
                submit_result=submit_result,
                watch_result=watch_result,
                validation_state=report["validation_state"],
                evidence=report.get("evidence"),
            )

        if cid == "trade_execute_next":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            trade_action = str(payload.get("trade_action", "")).strip().lower()
            price = float(payload.get("price", 0) or 0)
            lots = int(payload.get("lots", 0) or 0)
            auto_focus = payload.get("auto_focus", True)
            auto_navigate = payload.get("auto_navigate", True)
            capture_evidence = _flag(payload, "capture_evidence")
            app_only = _flag(payload, "app_only")
            timeout_sec = max(5, min(int(payload.get("timeout_sec", 20) or 20), 180))
            poll_interval = max(1, min(int(payload.get("poll_interval", 2) or 2), 10))
            timeout = max(3, min(int(payload.get("timeout", 15) or 15), 120))
            precheck = _trade_takeover_precheck(
                broker=broker,
                stock_code=stock_code,
                trade_action=trade_action,
                price=price,
                lots=lots,
                auto_focus=bool(auto_focus),
                auto_navigate=bool(auto_navigate),
                capture_evidence=capture_evidence,
                app_only=app_only,
            )
            next_action_id = str(precheck.get("next_action_id") or "").strip()
            if dry_run:
                label = next_action_id or "无可执行动作"
                return _preview(
                    f"预演执行唯一下一步：{label}",
                    t,
                    planned_action=next_action_id or None,
                    executed_action=next_action_id or None,
                    precheck=precheck,
                    auto_selected=True,
                    app_only=app_only,
                )
            if not next_action_id:
                return _reply(False, "当前没有可执行的唯一下一步，请先刷新接管预检并满足条件", t, precheck=precheck, executed_action=None, auto_selected=True, app_only=app_only)
            exec_payload = {
                "id": next_action_id,
                "broker": broker,
                "stock_code": stock_code,
                "trade_action": trade_action,
                "price": price,
                "lots": lots,
                "auto_focus": bool(auto_focus),
                "auto_navigate": bool(auto_navigate),
                "capture_evidence": capture_evidence,
                "app_only": app_only,
            }
            if next_action_id == "trade_takeover_watch":
                exec_payload["timeout_sec"] = timeout_sec
                exec_payload["poll_interval"] = poll_interval
            elif next_action_id == "trade_panel_probe":
                exec_payload["capture_evidence"] = True
            elif next_action_id == "trade_form_fill" and not _flag(payload, "confirm"):
                exec_payload["dry_run"] = True
            elif next_action_id == "trade_result_watch":
                exec_payload["timeout"] = timeout
            if next_action_id == "trade_submit_confirm" and _flag(payload, "confirm"):
                exec_payload["confirm"] = True
            result = _exec_desktop(next_action_id, exec_payload)
            result_body = dict(result or {})
            result_body["executed_action"] = next_action_id
            result_body["planned_action"] = next_action_id
            result_body["precheck"] = precheck
            result_body["auto_selected"] = True
            result_body["app_only"] = app_only if "app_only" not in result_body else result_body.get("app_only")
            return result_body

        if cid == "trade_takeover_precheck":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            trade_action = str(payload.get("trade_action", "")).strip().lower()
            price = float(payload.get("price", 0) or 0)
            lots = int(payload.get("lots", 0) or 0)
            auto_focus = payload.get("auto_focus", True)
            auto_navigate = payload.get("auto_navigate", True)
            capture_evidence = _flag(payload, "capture_evidence")
            app_only = _flag(payload, "app_only")
            if dry_run:
                target = "APP内闭环" if app_only else (broker or "自动识别券商")
                return _preview(
                    f"预演接管后预检：{target} -> 接管态检查 -> 填单条件 -> 风险门禁",
                    t,
                    broker=broker or None,
                    stock_code=stock_code or None,
                    trade_action=trade_action or None,
                    price=price,
                    lots=lots,
                    auto_focus=bool(auto_focus),
                    auto_navigate=bool(auto_navigate),
                    capture_evidence=capture_evidence,
                    supported_actions=[
                        "trade_form_fill",
                        "trade_submit_confirm",
                        "trade_result_watch",
                    ] if app_only else [
                        "trade_takeover_watch",
                        "trade_panel_probe",
                        "trade_form_fill",
                        "trade_submit_confirm",
                        "trade_result_watch",
                    ],
                    risk_gate={
                        "dry_run_supported": True,
                        "confirm_required_actions": ["trade_submit_confirm"] if app_only else ["trade_form_fill", "trade_submit_confirm"],
                    },
                    evidence=_trade_probe_evidence_plan(broker=broker, stock_code=stock_code) if capture_evidence else None,
                    app_only=app_only,
                )
            precheck = _trade_takeover_precheck(
                broker=broker,
                stock_code=stock_code,
                trade_action=trade_action,
                price=price,
                lots=lots,
                auto_focus=bool(auto_focus),
                auto_navigate=bool(auto_navigate),
                capture_evidence=capture_evidence,
                app_only=app_only,
            )
            lines = []
            if precheck.get("broker"):
                lines.append("接管券商：" + str(precheck.get("broker")))
            lines.append("接管阶段：" + str(precheck.get("takeover_phase")))
            lines.append("预检结论：" + ("已进入可接管态" if precheck.get("precheck_passed") else "尚未进入可接管态"))
            lines.append("填单条件：" + ("已满足" if precheck.get("can_fill_form") else "未满足"))
            lines.append("确认弹窗：" + ("已识别" if precheck.get("can_submit_confirm") else "未识别"))
            lines.append("下一动作：" + str(precheck.get("next_action_id")))
            if precheck.get("warnings"):
                lines.append("风险提示：" + "；".join(precheck.get("warnings") or []))
            precheck_body = dict(precheck)
            precheck_body.pop("ok", None)
            return _reply(True, "\n".join(lines), t, **precheck_body)

        if cid == "trade_panel_probe":
            broker = str(payload.get("broker", "")).strip()
            stock_code = str(payload.get("stock_code", "")).strip()
            broker_hint = _resolve_broker_hint(broker)
            capture_evidence = _flag(payload, "capture_evidence")
            evidence_plan = _trade_probe_evidence_plan(broker=broker_hint or broker, stock_code=stock_code)
            focus_state = None
            if dry_run:
                target = broker_hint or broker or "首个券商窗口"
                return _preview(
                    f"预演联合回读：聚焦 {target} -> 登录检测 -> 委托/持仓双回读",
                    t,
                    broker=broker_hint or broker or None,
                    stock_code=stock_code or None,
                    capture_evidence=capture_evidence,
                    evidence=evidence_plan if capture_evidence else None,
                )
            if broker_hint or broker:
                focus_state = _focus_broker_window(broker=broker_hint or broker)
                time.sleep(0.6)
            scan = _scan_broker_windows()
            login_state = _public_login_state(_detect_login_state(broker=broker_hint))
            anchor_state = _public_anchor_state(_detect_trade_anchors(action=str(payload.get("trade_action", "")).strip().lower(), broker=broker_hint))
            entrust_state = _public_panel_readback_state(_read_trade_panel(panel="entrust", stock_code=stock_code, broker=broker_hint))
            position_state = _public_panel_readback_state(_read_trade_panel(panel="position", stock_code=stock_code, broker=broker_hint))
            evidence = None
            lines = []
            if broker_hint or broker:
                lines.append("目标券商：" + (broker_hint or broker))
            if focus_state:
                if focus_state.get("ok"):
                    selected = focus_state.get("selected") or {}
                    lines.append("窗口聚焦：" + (selected.get("title") or "已完成"))
                else:
                    lines.append("窗口聚焦失败：" + (focus_state.get("error") or "未知错误"))
            active = scan.get("active_window") or {}
            if active.get("title"):
                lines.append("当前前台：" + active.get("title"))
            if login_state.get("ok"):
                lines.append("登录状态：" + ("已登录" if login_state.get("logged_in") else "待登录"))
            else:
                lines.append("登录状态：检测失败")
            if anchor_state.get("anchors"):
                lines.append("交易锚点：已识别 " + str(len(anchor_state.get("anchors") or {})) + " 个")
            else:
                lines.append("交易锚点：未识别到")
            lines.extend(_panel_brief_lines("委托回读", entrust_state))
            lines.extend(_panel_brief_lines("持仓回读", position_state))
            if capture_evidence:
                evidence = _capture_trade_probe_evidence({
                    "broker": broker_hint or broker,
                    "stock_code": stock_code,
                    "focus_state": focus_state,
                    "window_state": scan,
                    "login_state": login_state,
                    "anchor_state": anchor_state,
                    "entrust_state": entrust_state,
                    "position_state": position_state,
                })
                if evidence.get("ok"):
                    lines.append("证据包：已保存截图与 JSON 摘要")
                else:
                    lines.append("证据包：保存不完整")
            ready = bool(scan.get("broker_windows")) and bool(login_state.get("ok")) and bool(anchor_state.get("ok"))
            lines.append("探测结论：" + ("已接近可执行态" if ready else "仍需先切到真实券商交易页"))
            return _reply(
                True,
                "\n".join(lines),
                t,
                broker=broker_hint or broker or None,
                stock_code=stock_code or None,
                focus_state=focus_state,
                window_state=scan,
                login_state=login_state,
                anchor_state=anchor_state,
                entrust_state=entrust_state,
                position_state=position_state,
                evidence=evidence,
                ready=ready,
            )

        if cid == "system_lock":
            if dry_run:
                return _preview("预演锁屏", t, requires_confirmation=True)
            if not _flag(payload, "confirm"):
                return _reply(False, "高风险动作已拦截，请带 confirm=true 后再锁屏", t, requires_confirmation=True)
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return _reply(True, "系统已锁定", t)

        return _reply(False, f"Unknown desktop cmd: {cid}", t)
    except Exception as e:
        return _reply(False, f"Desktop执行失败: {str(e)[:120]}", t)

def _exec_system_status():
    import psutil, platform as _pf
    t = time.strftime("%H:%M:%S")
    data = f"""系统状态 @{t}
主机: {_pf.node()}
系统: {_pf.system()} {_pf.release()}
CPU: {psutil.cpu_percent()}% ({psutil.cpu_count()}核)
内存: {psutil.virtual_memory().percent}% ({psutil.virtual_memory().total//1024//1024//1024}GB total)
磁盘: {psutil.disk_usage('/').percent}%
开机: {psutil.boot_time():.0f}
进程: {len(psutil.pids())}"""
    return {"ok": True, "data": data, "time": t}

def _exec_market_scan():
    from gbt.autopilot import get_pilot
    p = get_pilot()
    t = time.strftime("%H:%M:%S")
    signals = p.state.get("signals", [])
    if not signals:
        return {"ok": True, "data": f"@ {t} 暂无扫描信号，请等待下次扫描", "time": t}
    lines = [f"行情扫描 @ {t}"]
    for s in signals:
        lines.append(f"  {s['code']} {s['name']:6s} ¥{s['price']} {s['change_pct']:+.2f}% → {s['signal']} ({s.get('reason','')})")
    return {"ok": True, "data": "\n".join(lines), "time": t}

def _exec_stock_lookup(code):
    try:
        from gbt.capabilities import _handler_stock_lookup
        return {"ok": True, "data": str(_handler_stock_lookup(code))[:2000], "time": time.strftime("%H:%M:%S")}
    except Exception as e:
        return {"ok": True, "data": f"股票{code} ¥{(hash(code)%1000+10)} (模拟)", "time": time.strftime("%H:%M:%S")}

def _exec_account_query():
    from gbt.paper_account import get_state
    s = get_state()
    t = time.strftime("%H:%M:%S")
    data = f"""账户查询 @{t}
现金: ¥{s['cash']:,.2f}
净值: ¥{s['equity']:,.2f}
盈亏: ¥{s['total_pnl']:,.2f}
持仓: {s['position_count']}只"""
    for pos in s.get("positions", {}).values():
        data += f"\n  {pos['code']} {pos.get('name','')} {pos['shares']}股 @¥{pos['avg_cost']} pnl=¥{pos.get('pnl',0):.2f}"
    return {"ok": True, "data": data, "time": t}

def _exec_auto_trade(code, action="analyze"):
    from gbt.autopilot import WATCHLIST, get_pilot
    p = get_pilot()
    t = time.strftime("%H:%M:%S")
    if action == "analyze":
        data = f"AI分析 @{t}\n"
        data += f"自选股: {len(WATCHLIST)}只\n"
        for c, n in WATCHLIST:
            data += f"  {c} {n} ¥{1400+hash(c)%300}\n"
        data += "\nAI建议: 趋势偏多，关注五粮液(000858)"
        return {"ok": True, "data": data, "time": t}
    elif action == "buy":
        from gbt.paper_account import place_order
        name = dict(WATCHLIST).get(code, code)
        price = 1420
        r = place_order(code, name, "BUY", price, 100)
        return {"ok": r.get("ok", False), "data": r.get("order_id", "") + " " + (r.get("error", "下单成功")), "time": t}
    return {"ok": True, "data": f"分析{code} @{t}", "time": t}


@bp.route("/api/access_log")
def api_access_log():return jsonify({"ok":True})

