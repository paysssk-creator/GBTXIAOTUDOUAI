"""GBT v2.0 — User Journey Test (模拟真实用户对话)"""
import requests, json, time, sys

URL = "http://127.0.0.1:8765/api/reason"

# === 用户真实场景 ===
# 场景1: 打开APP → 查看状态 → 了解能力
# 场景2: 看行情 → 查个股 → 分析
# 场景3: 自选股管理 → 大盘扫描
# 场景4: 操盘 → 选券商 → 分析
# 场景5: 系统控制 → 截图 → 快捷键

SCENARIOS = [
    # ── 场景1: 新用户入门 ──
    ("新用户-打开系统", [
        ("system_status", "你现在能干什么"),
        ("kb_query", "A股怎么开户交易"),
    ]),

    # ── 场景2: 行情查询 ──
    ("行情查看", [
        ("market_scan", "看看今天大盘行情怎么样"),
        ("stock_lookup", "查一下600519的状况"),
        ("watchlist", "我的自选股有哪些"),
    ]),

    # ── 场景3: 交易操作 ──
    ("交易操作", [
        ("auto_trade", "帮我分析600036值得买吗"),
        ("account_query", "我的账户还有多少钱"),
    ]),

    # ── 场景4: 操盘流水线 ──
    ("自主操盘", [
        ("auto_pipeline", "我想操盘"),
        ("auto_pipeline", "操盘平台用同花顺"),
    ]),

    # ── 场景5: 桌面控制 ──
    ("桌面操控", [
        ("browser_open", "打开百度帮我搜索A股新闻"),
        ("screenshot", "给我截个图看看"),
    ]),

    # ── 场景6: 系统辅助 ──
    ("系统辅助", [
        ("notify", "给我发个桌面通知提醒"),
        ("voice_speak", "语音读一下今天行情分析"),
        ("voice_list", "你能用什么声音说话"),
    ]),

    # ── 场景7: 高级功能 ──
    ("高级功能", [
        ("shortcuts_ref", "有什么快捷键可以用"),
        ("watcher_check", "守夜人还在监控吗"),
        ("code_exec", "执行打印hello gbt"),
    ]),
]

print("=" * 70)
print("  GBT v2.0 — USER JOURNEY TEST")
print("  Testing as a real human user would")
print("=" * 70)

total_tests = 0
pass_count = 0
fail_count = 0
scenario_pass = 0

for scenario_name, steps in SCENARIOS:
    print(f"\n{'='*60}")
    print(f"  [SCENE] {scenario_name}")
    print(f"{'='*60}")

    step_ok = 0
    for i, (expected_cap, user_input) in enumerate(steps):
        total_tests += 1
        t0 = time.time()
        try:
            r = requests.post(URL, json={"text": user_input, "mode": "quick"}, timeout=30)
            elapsed = time.time() - t0
            d = r.json()
            cap = d.get("capability", "?")
            conc = d.get("conclusion", "")[:200].replace("\n", " ")

            match = cap == expected_cap
            status = "PASS" if match else "ROUTE"
            symbol = "+" if match else "~"

            print(f"  [{symbol}] {user_input[:35]:35s} -> {cap:20s} ({elapsed*1000:4.0f}ms)")
            if conc:
                # show first meaningful line
                lines = [l.strip() for l in conc.split("\n") if l.strip()]
                if lines:
                    print(f"       {lines[0][:80]}")

            if match:
                pass_count += 1
                step_ok += 1
            else:
                fail_count += 1
                print(f"       EXPECTED: {expected_cap} GOT: {cap}")
        except Exception as e:
            fail_count += 1
            print(f"  [x] {user_input[:35]} -> ERROR: {str(e)[:60]}")

    if step_ok == len(steps):
        scenario_pass += 1

print()
print("=" * 70)
print("  USER JOURNEY SUMMARY")
print("=" * 70)
print(f"  Scenarios: {scenario_pass}/{len(SCENARIOS)} fully passed")
print(f"  Steps:     {pass_count}/{total_tests} routing correct")
print(f"  Accuracy:  {pass_count*100/total_tests:.0f}%")
print()
if pass_count == total_tests:
    print("  VERDICT: USER READY — All capabilities route correctly!")
elif pass_count >= total_tests * 0.9:
    print("  VERDICT: GOOD — Minor routing tweaks needed")
else:
    print("  VERDICT: NEEDS WORK — Check failures above")
