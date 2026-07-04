"""
GBT v2.0 自动化实时演示 — 打开浏览器, 逐项操作 APP
"""
import subprocess, time, requests, re, os, sys

CHROME = r"C:\Users\ADMIN\.cache\puppeteer\chrome\win64-150.0.7871.24\chrome-win64\chrome.exe"
API = "http://127.0.0.1:8765/api/reason"
HOME = "http://127.0.0.1:8765"

def call(text):
    """调用 GBT API"""
    try:
        r = requests.post(API, json={"text": text, "mode": "quick"}, timeout=30)
        d = r.json()
        return d.get("capability", "?"), d.get("conclusion", "")[:400]
    except Exception as e:
        return "error", str(e)[:100]

def show(title, text, expected):
    """展示一次操作"""
    print(f"\n  ┌{'─'*54}")
    print(f"  │  用户: {text}")
    cap, result = call(text)
    ok = "✓" if cap == expected else f"(期望{expected})"
    print(f"  │  GBT → {cap} {ok}")
    # 清理换行
    lines = result.replace("\n", " │ ").split("│")
    for line in lines[:8]:
        print(f"  │  {line.strip()[:70]}")
    print(f"  └{'─'*54}")
    time.sleep(0.5)

def open_browser(url):
    """打开Chrome"""
    try:
        subprocess.Popen([CHROME, "--new-window", url, "--window-size=1200,800"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

print("""
╔════════════════════════════════════════════════════╗
║   GBT v2.0 自主操盘 — 实时交互演示                  ║
╚════════════════════════════════════════════════════╝
""")

# 打开 APP
print("\n  ▶ 打开 GBT APP 首页...")
open_browser(HOME)
time.sleep(3)

# ── 场景1 ──
print("\n══════════════ 场景1: 用户入门 ══════════════")
show("系统能力",    "你现在能干什么",          "system_status")
show("A股知识",    "A股怎么开户交易",         "kb_query")

# ── 场景2 ──
print("\n══════════════ 场景2: 行情查询 ══════════════")
show("大盘扫描",   "看看今天大盘行情怎么样",   "market_scan")
show("查贵州茅台", "查一下600519的状况",       "stock_lookup")
show("自选股",     "我的自选股有哪些",         "watchlist")

# ── 场景3: 交易 ──
print("\n══════════════ 场景3: 交易分析 ══════════════")
show("AI分析",     "帮我分析600036值得买吗",   "auto_trade")
show("查账户",     "我的账户还有多少钱",       "account_query")

# ── 场景4: 操盘 ──
print("\n══════════════ 场景4: 自主操盘 ══════════════")
show("券商列表",   "我想操盘",                "auto_pipeline")
time.sleep(2)
show("选同花顺",   "操盘平台用同花顺",         "auto_pipeline")

# ── 场景5: 桌面 ──
print("\n══════════════ 场景5: 桌面控制 ══════════════")
show("搜索",       "打开百度帮我搜索A股新闻",  "browser_open")
show("截图",       "给我截个图看看",           "screenshot")

# ── 场景6 ──
print("\n══════════════ 场景6: 语音通知 ══════════════")
show("通知",       "给我发个桌面通知提醒",     "notify")
show("语音朗读",   "语音读一下今天行情分析",   "voice_speak")
show("音色列表",   "你能用什么声音说话",       "voice_list")

# ── 场景7 ──
print("\n══════════════ 场景7: 高级功能 ══════════════")
show("快捷键",     "有什么快捷键可以用",       "shortcuts_ref")
show("守夜人",     "守夜人还在监控吗",         "watcher_check")
show("执行代码",   "执行打印hello gbt",        "code_exec")

# ── 收尾 ──
print(f"\n{'='*60}")
cap, result = call("你现在能干什么")
print(f"  最终状态: system_status")
for line in result.replace("\n", "\n  ").split("\n")[:10]:
    print(f"  {line.strip()[:70]}")
print(f"\n{'='*60}")
print(f"  演示完成！{time.strftime('%H:%M:%S')}")
print(f"{'='*60}")
