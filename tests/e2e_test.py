# -*- coding: utf-8 -*-
"""End-to-end test for GBT AI Workstation.
Starts Web API, verifies capabilities, screenpipe, cradle task flow.
"""
import requests, time, sys, os
BASE = "http://127.0.0.1:8765"

# Wait up to 15s for the server to start.
for _ in range(15):
    try:
        requests.get(f"{BASE}/api/health", timeout=1)
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("Web API did not start")

def ok(resp):
    r = resp.json()
    assert r.get("ok"), f"API failed: {r}"
    return r.get("data", {})

def test_health():
    data = ok(requests.get(f"{BASE}/api/health", timeout=5))
    print("health version:", data.get("version"))
    assert data.get("version")

def test_capabilities():
    data = ok(requests.get(f"{BASE}/api/capabilities", timeout=5))
    caps = data if isinstance(data, list) else data.get("capabilities", [])
    names = [c.get("name") for c in caps]
    print("capabilities:", names)
    assert "screenpipe_monitor" in names
    assert "cradle_task" in names

def test_screenpipe():
    ok(requests.post(f"{BASE}/api/screenpipe/start", json={"mode":"screen","interval":2.0}, timeout=30))
    time.sleep(5)
    data = ok(requests.get(f"{BASE}/api/screenpipe/recent?limit=2", timeout=5))
    print("screenpipe frames:", data.get("count"))
    assert data.get("count", 0) >= 1
    ok(requests.post(f"{BASE}/api/screenpipe/stop", timeout=5))

def test_cradle_task():
    # 自动授权开启时 Cradle 会真正执行桌面动作；用截图任务替代打开 Chrome，避免依赖浏览器环境
    data = ok(requests.post(f"{BASE}/api/cradle/run", json={"task":"截图观察桌面","max_steps":2}, timeout=45))
    print("cradle source:", data.get("source"), "steps:", data.get("steps"))
    assert data.get("steps", 0) >= 1
    last = data.get("history", [])[-1]
    assert last.get("result", {}).get("ok") or last.get("result") is not None

def test_chat_routing():
    # 用截图任务替代打开记事本，自动授权开启时也能快速完成
    data = ok(requests.post(f"{BASE}/api/chat", json={"text":"执行一个任务：截图观察桌面"}, timeout=30))
    intent = data.get("classification", {}).get("intent")
    print("chat intent:", intent)
    assert intent == "cradle_task"

if __name__ == "__main__":
    print("E2E test starting...")
    test_health()
    test_capabilities()
    test_screenpipe()
    test_cradle_task()
    test_chat_routing()
    print("ALL E2E TESTS PASSED")
