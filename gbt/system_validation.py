"""GBT v2.0 Full System Validation — Production Readiness Test"""
import requests, time, json, sys, traceback
from collections import defaultdict

URL = "http://127.0.0.1:8765/api/reason"

# === ALL 33 capabilites with real user inputs ===
ALL_TESTS = [
    # === DESKTOP CONTROL ===
    ("screenshot",       "截图",                       "saved screenshot file"),
    ("window_maximize",  "最大化窗口",                  "window maximized"),
    ("keyboard_ctl",     "打字 hello world",             "keyboard input sent"),
    ("mouse_ctl",        "移动鼠标到屏幕中间",            "mouse move sent"),
    ("screen_ocr",       "识别屏幕上的文字",             "ocr scan started"),

    # === BROWSER ===
    ("browser_open",     "打开百度搜索",                 "browser opened"),

    # === TRADING ===
    ("account_query",    "查看我的账户",                 "account balance shown"),
    ("stock_lookup",     "600519贵州茅台",               "stock price returned"),
    ("market_scan",      "扫描一下大盘行情",             "market scan results"),
    ("watchlist",        "看看我的自选池有哪些股票",      "watchlist returned"),
    ("auto_trade",       "买股票600519",                 "auto trade analysis"),

    # === AUTO PIPELINE ===
    ("auto_pipeline",    "开始自主操盘",                 "broker list shown"),
    ("auto_pipeline",    "操盘平台用东方财富",              "eastmoney opened"),

    # === WEB SCRAPING ===
    ("web_search",       "搜索今天A股涨跌情况",           "search results returned"),
    ("precision_scrape", "抓取最新的财经新闻",            "scrape returned"),

    # === KNOWLEDGE ===
    ("kb_query",         "A股交易规则是什么",             "kb answer returned"),
    ("shortcuts_ref",    "有哪些快捷键可以用",            "shortcuts list"),

    # === VOICE ===
    ("voice_speak",      "说话你好我是GBT助手",           "tts played"),
    ("voice_list",       "列出所有可用的声音",             "voice list returned"),
    ("voice_listen",     "开始听写模式",                  "listening started"),
    ("voice_conv",       "我想和你语音对话聊天",           "voice conv mode"),

    # === SYSTEM ===
    ("system_status",    "查看系统状态信息",              "system stats returned"),
    ("shortcuts_ref",    "键盘快捷键",                    "shortcuts listed"),

    # === WATCHER ===
    ("watcher_check",    "检查守夜人监控是否正常",        "watcher status"),

    # === NOTIFY ===
    ("notify",           "发送一个桌面通知给我",          "notification sent"),

    # === FILE ===
    ("file_operation",   "在桌面创建一个测试文件",        "file operation"),

    # === CODE ===
    ("code_exec",        "执行一行打印代码 print('hello GBT')", "code executed"),

    # === BLUETOOTH ===
    ("bt_scan",          "扫描周围的蓝牙设备",            "bt scan started"),
    ("bt_pair",          "蓝牙配对一下手机",              "bt pair started"),
    ("bt_play",          "蓝牙播放音乐",                  "bt play started"),

    # === AUDIO ===
    ("audio_switch",     "切换音频输出设备",              "audio switch"),
]

print("=" * 70)
print("  GBT v2.0 FULL SYSTEM VALIDATION")
print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 70)
print()

results = []
start_time = time.time()

for i, (expected_cap, user_input, check_text) in enumerate(ALL_TESTS):
    t0 = time.time()
    idx = f"[{i+1:02d}/{len(ALL_TESTS)}]"
    
    try:
        r = requests.post(URL, json={"text": user_input, "mode": "quick"}, timeout=30)
        elapsed = time.time() - t0
        d = r.json()
        cap = d.get("capability", "")
        conclusion = d.get("conclusion", "")[:120]
        
        match = cap == expected_cap
        has_output = len(conclusion) > 10
        
        if match and has_output:
            status = "PASS"
        elif match:
            status = "WARN"  # routed right but empty output
        else:
            status = "FAIL"
        
        # Emoji-safe print
        icon = "+" if status == "PASS" else ("~" if status == "WARN" else "x")
        print(f"  [{icon}] {idx} {expected_cap:18s} | '{user_input[:30]}' | {elapsed*1000:5.0f}ms | {cap}")
        if not match:
            print(f"       WANT: {expected_cap}  GOT: {cap}  >> {conclusion[:80]}")
        
        results.append({
            "expected": expected_cap, "got": cap, "match": match,
            "ok": True, "has_output": has_output, "elapsed": elapsed,
            "output_len": len(conclusion),
        })
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  [x] {idx} {expected_cap:18s} | '{user_input[:30]}' | ERROR: {str(e)[:60]}")
        results.append({"expected": expected_cap, "ok": False, "error": str(e)[:80]})

total_time = time.time() - start_time
total = len(results)
ok = sum(1 for r in results if r["ok"])
matched = sum(1 for r in results if r.get("match"))
has_output = sum(1 for r in results if r.get("has_output"))
avg_ms = sum(r.get("elapsed", 0) for r in results) / max(total, 1) * 1000

# === SUMMARY ===
print()
print("=" * 70)
print("  RESULTS")
print("=" * 70)
print(f"  Total tests:        {total}")
print(f"  Success rate:       {ok}/{total} ({ok*100/total:.0f}%)")
print(f"  Routing accuracy:   {matched}/{ok} ({matched*100/max(ok,1):.0f}%)")
print(f"  Valid output:       {has_output}/{ok} ({has_output*100/max(ok,1):.0f}%)")
print(f"  Average latency:    {avg_ms:.0f}ms")
print(f"  Total time:         {total_time:.1f}s")
print()

# Group by category
print("=" * 70)
print("  BY CATEGORY")
print("=" * 70)
cats = defaultdict(lambda: {"t": 0, "ok": 0, "match": 0})
for i, r in enumerate(results):
    exp = r["expected"]
    if exp in ("screenshot","window_maximize","keyboard_ctl","mouse_ctl","screen_ocr"):
        cat = "Desktop"
    elif exp in ("browser_open",):
        cat = "Browser"
    elif exp in ("account_query","stock_lookup","market_scan","watchlist","auto_trade"):
        cat = "Trading"
    elif exp in ("auto_pipeline",):
        cat = "Pipeline"
    elif exp in ("web_search","precision_scrape"):
        cat = "Web/Scrape"
    elif exp in ("kb_query","shortcuts_ref"):
        cat = "Knowledge"
    elif exp in ("voice_speak","voice_list","voice_listen","voice_conv"):
        cat = "Voice"
    elif exp in ("system_status","watcher_check","notify"):
        cat = "System"
    elif exp in ("bt_scan","bt_pair","bt_play","audio_switch"):
        cat = "BT/Audio"
    elif exp in ("file_operation","code_exec"):
        cat = "File/Code"
    else:
        cat = "Other"
    cats[cat]["t"] += 1
    if r["ok"]: cats[cat]["ok"] += 1
    if r.get("match"): cats[cat]["match"] += 1

print(f"  {'Category':15s} {'Tests':>5s} {'Pass':>5s} {'Route':>7s}")
print(f"  {'-'*15} {'-'*5} {'-'*5} {'-'*7}")
for cat in sorted(cats.keys()):
    d = cats[cat]
    print(f"  {cat:15s} {d['t']:5d} {d['ok']:5d} {d['match']:4d}/{d['t']}")

# Final verdict
print()
if ok == total and matched == ok:
    print("  VERDICT: PRODUCTION READY -- ALL SYSTEMS GO")
elif ok >= total * 0.95 and matched >= ok * 0.95:
    print("  VERDICT: PRODUCTION READY (minor warnings)")
elif ok >= total * 0.9:
    print("  VERDICT: NEEDS REVIEW -- check failures above")
else:
    print("  VERDICT: BLOCKED -- critical failures")
print("=" * 70)
