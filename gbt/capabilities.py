# -*- coding: utf-8 -*-
"""
capabilities.py -- GBT capability registry
v3.0: +OCR +voice +scrape +pipeline
"""
import os, sys, re, logging, time
from gbt.router import Capability, router

L = logging.getLogger("GBT.Capabilities")

def _handler_maximize(text):
    "\u6700\u5927\u5316/\u5168\u5c4f\u7a97\u53e3"
    try:
        from gbt.desktop_ctl import desktop_ctl
        desktop_ctl.maximize_window()
        return "\u7a97\u53e3\u5df2\u6700\u5927\u5316"
    except Exception as e:
        return f"\u6700\u5927\u5316\u5931\u8d25: {e}"

def _handler_screenshot(text):
    "\u5c4f\u5e55\u622a\u56fe"
    try:
        import pyautogui
        ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
        os.makedirs(ss_dir, exist_ok=True)
        fp = os.path.join(ss_dir, f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(fp)
        return f"\u622a\u56fe\u5df2\u4fdd\u5b58 \u2192 {fp}"
    except Exception as e:
        return f"\u622a\u56fe\u5931\u8d25: {e}"

def _handler_stock_lookup(text):
    "\u67e5\u8be2\u80a1\u7968\u5b9e\u65f6\u884c\u60c5"
    m = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
    if not m:
        return "\u672a\u627e\u5230\u80a1\u7968\u4ee3\u7801\uff08\u9700\u89816\u4f4d\u6570\u5b57\u4ee3\u7801\uff09"
    code = m.group(1)
    trader = router.get_dep("trader")
    if not trader:
        return "\u4ea4\u6613\u5f15\u64ce\u672a\u5c31\u7eea"
    try:
        q = trader.fetch_quote([code])
        if code in q:
            qt = q[code]
            name = getattr(qt, "name", code)
            price = getattr(qt, "price", 0)
            pct = getattr(qt, "change_pct", 0)
            return f"{name}({code}): \u00a5{price} | {pct:+.2f}%"
    except Exception as e:
        return f"\u67e5\u8be2\u5931\u8d25: {e}"
    return f"\u672a\u627e\u5230 {code} \u7684\u884c\u60c5\u6570\u636e"

def _handler_scan_market(text):
    "\u626b\u63cf\u5168\u5e02\u573a/\u81ea\u9009\u80a1"
    return {"ok": True, "capability": "market_scan", "text": text}

def _handler_watchlist(text):
    "\u67e5\u770b\u81ea\u9009\u80a1\u5217\u8868"
    return {"ok": True, "capability": "watchlist", "text": text}

def _handler_trade(text):
    "\u89e6\u53d1\u81ea\u4e3b\u4ea4\u6613\u5206\u6790"
    brain = router.get_dep("brain")
    if not brain:
        return "\u5927\u8111\u672a\u5c31\u7eea"
    try:
        result = brain.think(text) if hasattr(brain, "think") else {"action": "analyze", "text": text}
        return {"ok": True, "result": result}
    except Exception as e:
        return f"\u4ea4\u6613\u5206\u6790\u5931\u8d25: {e}"

def _handler_system_status(text):
    "\u67e5\u770bGBT\u7cfb\u7edf\u72b6\u6001"
    trader = router.get_dep("trader")
    watcher = router.get_dep("watcher")
    brain = router.get_dep("brain")
    lines = []
    if brain and hasattr(brain, "get_status"):
        lines.append(f"\u5927\u8111: {brain.get_status()}")
    else:
        lines.append("\u5927\u8111: \u5df2\u505c\u6b62")
    if trader:
        auto = getattr(trader, "auto_trade", False)
        wl_count = len(getattr(trader, "WATCHLIST", {}))
        lines.append(f"\u4ea4\u6613: auto_trade={auto} | {wl_count} \u81ea\u9009")
    if watcher and hasattr(watcher, "get_status"):
        lines.append(f"\u76d1\u63a7: {watcher.get_status()}")
    return "\n".join(lines)

def _handler_watcher_check(text):
    "\u5b88\u591c\u4eba\u5b89\u5168\u76d1\u63a7"
    return {"ok": True, "capability": "watcher_check", "text": text}

def _handler_account(text):
    "\u67e5\u770b\u6a21\u62df\u8d26\u6237"
    return {"ok": True, "capability": "account_query", "text": text}

def _handler_notify(text):
    "\u53d1\u9001Windows\u684c\u9762\u901a\u77e5"
    msg = text.replace("\u901a\u77e5", "").replace("\u63d0\u9192\u6211", "").strip() or "GBT \u63d0\u9192"
    try:
        from gbt.desktop_ctl import desktop_ctl
        return desktop_ctl.notify(msg)
    except Exception as e:
        return f"\u901a\u77e5\u5931\u8d25: {e}"

def _handler_web_search(text):
    "\u7f51\u7edc\u641c\u7d22\u83b7\u53d6\u5b9e\u65f6\u4fe1\u606f"
    return {"ok": True, "capability": "web_search", "text": text}

def _handler_file_op(text):
    "\u6587\u4ef6\u8bfb\u5199\u64cd\u4f5c"
    return {"ok": True, "capability": "file_operation", "text": text}

def _handler_code_exec(text):
    "\u6267\u884cPython/Shell\u4ee3\u7801"
    return {"ok": True, "capability": "code_exec", "text": text}

def _handler_screen_ocr(text):
    "\u5c4f\u5e55OCR\u8bc6\u522b\u684c\u9762\u6587\u5b57"
    try:
        from gbt.ai_operator import get_ai_operator
        op = get_ai_operator()
        result = op.observe()
        return {"ok": True, "ocr": result.get("ocr", {}), "image_size": result.get("image_size")}
    except Exception as e:
        return f"OCR\u5931\u8d25: {e}"

def _handler_voice_speak(text):
    "Windows\u8bed\u97f3\u6717\u8bfb\u8f93\u51fa"
    try:
        from gbt.screen_ai import Voice
        return Voice.speak(text)
    except Exception as e:
        return f"\u8bed\u97f3\u5931\u8d25: {e}"

def _handler_login_detect(text):
    "OCR\u68c0\u6d4b\u5238\u5546\u767b\u5f55\u72b6\u6001"
    return {"ok": True, "capability": "login_detect", "text": text}

def _handler_precision_scrape(text):
    "\u591a\u6e90\u7cbe\u51c6\u8d44\u8baf\u6293\u53d6\u4ea4\u53c9\u9a8c\u8bc1"
    return {"ok": True, "capability": "precision_scrape", "text": text}

def _handler_auto_pipeline(text):
    "\u81ea\u4e3b\u64cd\u76d8\u6d41\u6c34\u7ebf"
    try:
        from gbt.screen_ai import AutoPipeline
        pipe = AutoPipeline()
        return pipe.run_login_flow("https://jywg.eastmoney.com/", "\u4e1c\u65b9\u8d22\u5bcc")
    except Exception as e:
        return f"\u6d41\u6c34\u7ebf\u5931\u8d25: {e}"

def _handler_browser_open(text):
    "\u6253\u5f00\u6d4f\u89c8\u5668/\u7f51\u9875"
    url = "https://www.bing.com"
    m = re.search(r"(https?://[^\s\u4e00-\u9fff]+)", text)
    if m:
        url = m.group(1)
    try:
        os.startfile(url)
    except Exception as e:
        return f"\u6253\u5f00\u6d4f\u89c8\u5668\u5931\u8d25: {e}"
    return f"\u5df2\u6253\u5f00\u6d4f\u89c8\u5668 \u2192 {url}"

def register_all():
    "Register all capabilities"
    caps = [
        Capability("window_maximize", "desktop", "\u6700\u5927\u5316/\u5168\u5c4f\u7a97\u53e3", ["\u6700\u5927\u5316", "\u5168\u5c4f", "\u6700\u5927\u5316\u7a97\u53e3", "\u653e\u5927", "\u7a97\u53e3\u653e\u5927", "\u7a97\u53e3\u6700\u5927\u5316"], _handler_maximize, priority=7),
        Capability("screenshot", "desktop", "\u5c4f\u5e55\u622a\u56fe", ["\u622a\u56fe", "\u622a\u5c4f", "\u5c4f\u5e55\u622a\u56fe", "\u62cd\u5c4f", "\u622a\u4e2a\u56fe", "\u62cd\u4e2a"], _handler_screenshot, priority=6),
        Capability("stock_lookup", "trading", "\u67e5\u8be2\u80a1\u7968\u5b9e\u65f6\u884c\u60c5", ["\u884c\u60c5", "\u67e5\u8be2", "\u80a1\u4ef7", "\u591a\u5c11\u94b1", "\u6da8\u8dcc", "\u8d70\u52bf", "\u5206\u6790"], _handler_stock_lookup, priority=8, requires=["trader"]),
        Capability("market_scan", "trading", "\u626b\u63cf\u5168\u5e02\u573a/\u81ea\u9009\u80a1", ["\u626b\u63cf", "\u5e02\u573a", "\u5927\u76d8", "\u81ea\u9009", "scan"], _handler_scan_market, priority=7, requires=["trader"]),
        Capability("watchlist", "trading", "\u67e5\u770b\u81ea\u9009\u80a1\u5217\u8868", ["\u81ea\u9009\u80a1", "watchlist", "\u6301\u4ed3\u5217\u8868"], _handler_watchlist, priority=5, requires=["trader"]),
        Capability("auto_trade", "trading", "\u89e6\u53d1\u81ea\u4e3b\u4ea4\u6613\u5206\u6790", ["\u4e70\u5165", "\u5356\u51fa", "\u4e70\u80a1", "\u5356\u80a1", "\u4e70\u8fdb", "\u5356\u6389", "\u4ea4\u6613", "\u64cd\u76d8", "\u4e0b\u5355", "\u4e70", "\u5356", "buy", "sell"], _handler_trade, priority=9, requires=["trader", "brain"]),
        Capability("system_status", "system", "\u67e5\u770bGBT\u7cfb\u7edf\u72b6\u6001", ["\u7cfb\u7edf\u72b6\u6001", "\u8fd0\u884c\u72b6\u6001", "GBT\u72b6\u6001", "\u670d\u52a1\u72b6\u6001", "\u72b6\u6001"], _handler_system_status, priority=6, requires=["brain"]),
        Capability("watcher_check", "system", "\u5b88\u591c\u4eba\u5b89\u5168\u76d1\u63a7", ["\u76d1\u63a7\u72b6\u6001", "\u5b89\u5168\u76d1\u63a7", "\u5b88\u591c\u4eba", "\u5b89\u5168\u68c0\u67e5", "watcher", "\u76d1\u63a7"], _handler_watcher_check, priority=6, requires=["watcher"]),
        Capability("account_query", "system", "\u67e5\u770b\u6a21\u62df\u8d26\u6237", ["\u8d26\u6237", "\u8d44\u91d1", "\u4f59\u989d", "\u76c8\u4e8f", "\u6301\u4ed3", "\u4ed3\u4f4d", "\u94b1"], _handler_account, priority=6, requires=["account"]),
        Capability("notify", "notification", "\u53d1\u9001Windows\u684c\u9762\u901a\u77e5", ["\u901a\u77e5", "\u63d0\u9192\u6211", "\u63d0\u9192", "\u5f39\u7a97"], _handler_notify, priority=4),
        Capability("web_search", "hacker", "\u7f51\u7edc\u641c\u7d22\u83b7\u53d6\u5b9e\u65f6\u4fe1\u606f", ["\u641c\u7d22", "\u67e5\u4e00\u4e0b", "search", "\u767e\u5ea6", "\u8c37\u6b4c", "\u641c\u7d22\u65b0\u95fb"], _handler_web_search, priority=11),
        Capability("file_operation", "hacker", "\u6587\u4ef6\u8bfb\u5199\u64cd\u4f5c", ["\u8bfb\u6587\u4ef6", "\u5199\u6587\u4ef6", "\u6587\u4ef6", "\u4ee3\u7801", "\u7f16\u8f91"], _handler_file_op, priority=6),
        Capability("code_exec", "hacker", "\u6267\u884cPython/Shell\u4ee3\u7801", ["\u6267\u884c\u4ee3\u7801", "\u8fd0\u884c\u4ee3\u7801", "python", "```", "shell", "cmd"], _handler_code_exec, priority=8, requires=["desktop_ctl"]),
        Capability("screen_ocr", "desktop", "\u5c4f\u5e55OCR\u8bc6\u522b\u684c\u9762\u6587\u5b57", ["ocr", "\u8bc6\u522b\u5c4f\u5e55", "\u770b\u5c4f\u5e55", "\u8bfb\u5c4f\u5e55", "\u5c4f\u5e55\u6587\u5b57", "\u8bc6\u56fe", "OCR\u8bc6\u522b"], _handler_screen_ocr, priority=7),
        Capability("voice_speak", "notification", "Windows\u8bed\u97f3\u6717\u8bfb\u8f93\u51fa", ["\u8bf4", "\u6717\u8bfb", "\u8bed\u97f3", "\u8bb2\u8bdd", "speak", "\u64ad\u62a5"], _handler_voice_speak, priority=5),
        Capability("login_detect", "desktop", "OCR\u68c0\u6d4b\u5238\u5546\u767b\u5f55\u72b6\u6001", ["\u68c0\u6d4b\u767b\u5f55", "\u767b\u5f55\u68c0\u6d4b", "\u767b\u5f55\u72b6\u6001", "\u662f\u5426\u767b\u5f55"], _handler_login_detect, priority=8, requires=["desktop_ctl"]),
        Capability("precision_scrape", "hacker", "\u591a\u6e90\u7cbe\u51c6\u8d44\u8baf\u6293\u53d6\u4ea4\u53c9\u9a8c\u8bc1", ["\u6293\u53d6", "\u8d44\u8baf", "\u65b0\u95fb", "scrape", "\u884c\u60c5\u5feb\u8baf", "\u7cbe\u51c6"], _handler_precision_scrape, priority=10),
        Capability("auto_pipeline", "trading", "\u81ea\u4e3b\u64cd\u76d8\u6d41\u6c34\u7ebf(\u5f00\u6d4f\u89c8\u5668\u2192\u68c0\u6d4b\u767b\u5f55\u2192\u63a5\u624b)", ["\u64cd\u76d8\u6d41\u6c34\u7ebf", "\u64cd\u76d8", "\u81ea\u52a8\u64cd\u76d8", "\u5f00\u59cb\u64cd\u76d8", "\u81ea\u4e3b\u4ea4\u6613", "\u81ea\u52a8\u4ea4\u6613"], _handler_auto_pipeline, priority=10, requires=["trader", "brain"]),
        Capability("browser_open", "desktop", "\u6253\u5f00\u6d4f\u89c8\u5668/\u7f51\u9875", ["\u6253\u5f00\u6d4f\u89c8\u5668", "\u6253\u5f00edge", "\u6253\u5f00chrome", "\u6253\u5f00\u7f51\u9875", "\u4e0a\u7f51", "\u6d4f\u89c8"], _handler_browser_open, priority=9),
    ]
    for cap in caps:
        router.register(cap)
    L.info(f"Registered {len(caps)} capabilities")
    return len(caps)

register_all()
