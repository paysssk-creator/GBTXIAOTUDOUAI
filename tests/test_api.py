"""
test_api.py — GBT API 冒烟测试
验证所有核心端点可访问
"""
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API = "http://localhost:8765/api"
ENDPOINTS = [
    "/status",
    "/brain/status",
    "/trader/status",
    "/watcher/status",
    "/trader/journal",
    "/trader/sessions",
]

def test_endpoints():
    passed = 0
    failed = 0
    
    for ep in ENDPOINTS:
        try:
            r = urllib.request.urlopen(f"{API}{ep}", timeout=5)
            if r.status == 200:
                passed += 1
                print(f"  PASS  {ep} ({r.status})")
            else:
                failed += 1
                print(f"  FAIL  {ep} ({r.status})")
        except Exception as e:
            failed += 1
            print(f"  ERROR {ep}: {e}")
    
    print(f"\nAPI Test: {passed}/{len(ENDPOINTS)} PASS")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(test_endpoints())
