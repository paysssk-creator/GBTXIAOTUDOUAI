"""
test_router.py — 智能路由器全能力测试
每次修改能力后运行此测试确保无回归
"""
import sys, io, json, urllib.request, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API = "http://localhost:8877/api"
TIMEOUT = 25

TEST_CASES = [
    # (name, text, expected_cap, must_contain)
    ("browser_open", "打开浏览器", "browser_open", "已打开"),
    ("window_maximize", "最大化窗口", "window_maximize", "已最大化"),
    ("screenshot", "截图保存", "screenshot", "截图已保存"),
    ("stock_lookup", "查询600519行情", "stock_lookup", "600519"),
    ("market_scan", "扫描市场", "market_scan", "自选池"),
    ("watchlist", "自选股列表", "watchlist", "自选池"),
    ("auto_trade", "买入600036", "auto_trade", "600036"),
    ("system_status", "系统状态", "system_status", "大脑"),
    ("watcher_check", "安全监控", "watcher_check", "守夜人"),
    ("account_query", "账户余额", "account_query", "模拟账户"),
    ("notify", "提醒测试", "notify", "已发送"),
]

def run_tests():
    passed = 0
    failed = 0
    
    # Check GBT is running
    try:
        urllib.request.urlopen(f"{API}/status", timeout=5)
    except:
        print("ERROR: GBT not running on port 8877")
        return 1
    
    for name, text, expected_cap, must_contain in TEST_CASES:
        data = json.dumps({"text": text, "mode": "CHAIN"}).encode("utf-8")
        req = urllib.request.Request(
            f"{API}/reason",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            r = urllib.request.urlopen(req, timeout=TIMEOUT)
            result = json.loads(r.read())
            cap = result.get("capability", "")
            conclusion = result.get("conclusion", "")
            routed = result.get("routed", False)
            
            if expected_cap is None:
                # Fallback to LLM: should NOT be routed
                ok = not routed
            else:
                ok = (cap == expected_cap) and (must_contain in conclusion if must_contain else True)
            
            if ok:
                passed += 1
                print(f"  PASS  {name}: {conclusion[:60]}")
            else:
                failed += 1
                print(f"  FAIL  {name}: cap={cap} expect={expected_cap}")
                print(f"         conclusion={conclusion[:80]}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {name}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{len(TEST_CASES)} PASS")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_tests())
