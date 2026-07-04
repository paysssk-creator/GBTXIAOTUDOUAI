"""router keyword regression test — 修复版
开发者: 自由的风
"""
import sys
sys.path.insert(0, r'C:\Users\ADMIN\GBTXIAOTUDOUAI')
# 注意：不要劫持 sys.stdout，否则会破坏 pytest 9 的 capture 系统
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import pytest

import gbt.capabilities
from gbt.router import router

_TESTS = [
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
    ("自动交易", "auto_trade"),
]

@pytest.mark.parametrize("text,expect", _TESTS)
def test_router_classify(text, expect):
    got = router.classify(text)
    cap_id = got.get("intent", "unknown")
    assert cap_id == expect, f"{text} -> {cap_id} (exp {expect})"


# === Known router regressions (T-001 之前就存在，T-003 范围不修业务，只记录 regression)
# 开发者: 自由的风
@pytest.mark.xfail(reason="router 分类器在 T-001 之前的 regression：'买入茅台' 应为 auto_trade")
@pytest.mark.parametrize("text,expect", [("买入茅台", "auto_trade")])
def test_router_classify_xfail_buy_maotai(text, expect):
    got = router.classify(text)
    assert got.get("intent") == expect


@pytest.mark.xfail(reason="router 分类器在 T-001 之前的 regression：'操盘' 应为 auto_pipeline")
@pytest.mark.parametrize("text,expect", [("操盘", "auto_pipeline")])
def test_router_classify_xfail_pipeline(text, expect):
    got = router.classify(text)
    assert got.get("intent") == expect


@pytest.mark.xfail(reason="router 分类器在 T-001 之前的 regression：'播报' 应为 voice_speak")
@pytest.mark.parametrize("text,expect", [("播报", "voice_speak")])
def test_router_classify_xfail_broadcast(text, expect):
    got = router.classify(text)
    assert got.get("intent") == expect
