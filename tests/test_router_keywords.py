"""router keyword regression test — 修复版"""
import sys, io
sys.path.insert(0, r'C:\Users\ADMIN\GBTXIAOTUDOUAI')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import gbt.capabilities
from gbt.router import router

tests = [
    ("打开浏览器", "browser_open"),
    ("ocr", "screen_ocr"),
    ("朗读", "voice_speak"),
    ("截图", "screenshot"),
    ("买入茅台", "auto_trade"),
    ("账户余额", "account_query"),
    ("搜索新闻", "web_search"),
    ("检测登录", "login_detect"),
    ("抓取资讯", "precision_scrape"),
    ("操盘", "auto_pipeline"),
    ("系统状态", "system_status"),
    ("执行代码", "code_exec"),
    ("读文件", "file_operation"),
    ("播报", "voice_speak"),
    ("守夜人", "watcher_check"),
    ("文件操作", "file_operation"),
    ("python代码", "code_exec"),
    ("读屏幕文字", "screen_ocr"),
    ("自动交易", "auto_pipeline"),
]

ok = 0
fail = 0
for text, expect in tests:
    got = router.classify(text)
    cap_id = got.get("intent", "unknown")
    if cap_id == expect:
        ok += 1
    else:
        fail += 1
        print(f"  FAIL: {text} -> {cap_id} (exp {expect})")

print(f"router keywords: {ok}/{ok+fail} PASS")
sys.exit(1 if fail > 0 else 0)
