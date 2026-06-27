import subprocess, time, requests, os, sys
BASE = "http://127.0.0.1:8765"
def start():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.Popen([sys.executable, "-m", "gbt.web_api"], env=env)
def main():
    p = start()
    time.sleep(3)
    passed = 0; failed = 0
    tests = [
        ("health", lambda: requests.get(f"{BASE}/api/health")),
        ("capabilities", lambda: requests.get(f"{BASE}/api/capabilities")),
        ("dashboard", lambda: requests.get(f"{BASE}/")),
        ("chat browser", lambda: requests.post(f"{BASE}/api/chat", json={"text":"打开百度"})),
        ("chat stock", lambda: requests.post(f"{BASE}/api/chat", json={"text":"查股票600519"})),
        ("hacker screen_ocr", lambda: requests.post(f"{BASE}/api/hacker/exec", json={"id":"screen_ocr","action":"run"})),
        ("nanobrowser status", lambda: requests.get(f"{BASE}/api/nanobrowser/status")),
        ("cradle status", lambda: requests.get(f"{BASE}/api/cradle/status")),
    ]
    for name, fn in tests:
        try:
            r = fn()
            ok = r.status_code == 200 and (r.json().get("ok") is True if r.headers.get("content-type","").startswith("application/json") else "GBT" in r.text)
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {r.status_code}")
            if ok: passed += 1
            else: failed += 1; print(r.text[:200])
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    p.terminate(); p.wait(timeout=3)
    print(f"\nE2E result: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
if __name__ == "__main__":
    main()
