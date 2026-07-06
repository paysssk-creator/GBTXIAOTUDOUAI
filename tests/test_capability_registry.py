"""tests/test_capability_registry.py · 能力注册表门禁测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import gbt.capabilities  # noqa: F401
from gbt.router import router


EXPECTED_CAPABILITY_IDS = [
    "browser_open",
    "window_maximize",
    "screenshot",
    "stock_lookup",
    "market_scan",
    "watchlist",
    "auto_trade",
    "system_status",
    "watcher_check",
    "account_query",
    "notify",
    "web_search",
    "file_operation",
    "code_exec",
    "screen_ocr",
    "voice_speak",
    "login_detect",
    "precision_scrape",
    "auto_pipeline",
    "kb_query",
    "voice_list",
    "voice_listen",
    "voice_conv",
    "audio_switch",
    "keyboard_ctl",
    "mouse_ctl",
    "bt_scan",
    "bt_pair",
    "bt_play",
    "shortcuts_ref",
    "recall_op",
    "op_summary",
    "op_context",
]


@pytest.mark.parametrize("cap_id", EXPECTED_CAPABILITY_IDS)
def test_capability_registry_contains_expected_ids(cap_id):
    """当前能力注册表必须稳定包含既定能力 ID。"""
    assert cap_id in router.capabilities


def test_capability_registry_count_and_identity():
    """能力总数和 ID 集合必须与当前注册表基线一致。"""
    actual_ids = sorted(router.capabilities.keys())
    assert actual_ids == sorted(EXPECTED_CAPABILITY_IDS)
    assert len(actual_ids) == 33


@pytest.mark.parametrize("cap_id", EXPECTED_CAPABILITY_IDS)
def test_capability_registry_metadata_integrity(cap_id):
    """每项能力都必须具备可执行的基础元数据。"""
    cap = router.capabilities[cap_id]
    assert cap.name == cap_id
    assert isinstance(cap.category, str) and cap.category
    assert isinstance(cap.description, str) and cap.description
    assert isinstance(cap.priority, int) and 1 <= cap.priority <= 10
    assert isinstance(cap.keywords, list) and len(cap.keywords) >= 1
    assert callable(cap.handler)
    assert router._handlers.get(cap_id) is cap.handler
    assert isinstance(cap.requires, list)


@pytest.mark.parametrize(
    "cap_id, probe_text",
    [
        ("browser_open", "打开浏览器"),
        ("window_maximize", "最大化窗口"),
        ("screenshot", "截图"),
        ("stock_lookup", "查股票 600519"),
        ("market_scan", "扫描市场"),
        ("watchlist", "查看自选股"),
        ("auto_trade", "买股票 600519"),
        ("system_status", "系统状态"),
        ("watcher_check", "守夜人"),
        ("account_query", "账户余额"),
        ("notify", "提醒我"),
        ("web_search", "搜索新闻"),
        ("file_operation", "读文件"),
        ("code_exec", "执行 python 代码"),
        ("screen_ocr", "识别屏幕"),
        ("voice_speak", "朗读"),
        ("login_detect", "检测登录"),
        ("precision_scrape", "抓取资讯"),
        ("auto_pipeline", "开始操盘"),
        ("kb_query", "风控"),
        ("voice_list", "列出声音"),
        ("voice_listen", "听我说"),
        ("voice_conv", "语音对话"),
        ("audio_switch", "切换音频"),
        ("keyboard_ctl", "输入文字"),
        ("mouse_ctl", "鼠标点击"),
        ("bt_scan", "扫描蓝牙"),
        ("bt_pair", "蓝牙配对"),
        ("bt_play", "播放音乐"),
        ("shortcuts_ref", "快捷键大全"),
        ("recall_op", "最近做了什么"),
        ("op_summary", "操作统计"),
        ("op_context", "决策上下文"),
    ],
)
def test_capability_registry_match_probes(cap_id, probe_text):
    """每项能力至少要能被一个稳定探针文本命中。"""
    cap = router.capabilities[cap_id]
    assert cap.matches(probe_text), f"{cap_id} 未命中探针文本: {probe_text}"

