"""tests/test_screen_ai_trade_rows.py · OCR 交易表格结构化回读测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gbt.screen_ai import ScreenOCR


def test_build_entrust_panel_rows_from_ocr_lines():
    lines = [
        "今日委托 证券代码 证券名称 买卖方向 状态 委托价 委托数量",
        "600519 贵州茅台 买入 已报 1420.55 100 142055.00",
        "000858 五粮液 卖出 已成 128.30 200 25660.00",
    ]

    rows = ScreenOCR._build_panel_rows("entrust", lines, stock_code="")

    assert len(rows) == 2
    assert rows[0]["code"] == "600519"
    assert rows[0]["action"] == "买入"
    assert rows[0]["status"] == "已报"
    assert rows[0]["price"] == "1420.55"
    assert rows[0]["quantity"] == "100"
    assert rows[0]["amount"] == "142055.00"


def test_build_position_panel_rows_skips_header_and_extracts_fields():
    lines = [
        "持仓查询 证券代码 证券名称 股份余额 可卖数量 成本价 市值 参考盈亏",
        "600519 贵州茅台 100 100 1420.55 142055.00 5600.00",
        "000001 平安银行 200 200 12.31 2462.00 -120.00",
    ]

    rows = ScreenOCR._build_panel_rows("position", lines, stock_code="")

    assert len(rows) == 2
    assert rows[0]["code"] == "600519"
    assert rows[0]["quantity"] == "100"
    assert rows[0]["available"] == "100"
    assert rows[0]["price"] == "1420.55"
    assert rows[0]["market_value"] == "142055.00"
    assert rows[0]["profit"] == "5600.00"


def test_group_words_into_rows_rebuilds_split_ocr_words():
    words = [
        {"text": "证券代码", "x": 20, "y": 10, "w": 60, "h": 18},
        {"text": "委托价", "x": 120, "y": 10, "w": 50, "h": 18},
        {"text": "数量", "x": 210, "y": 11, "w": 35, "h": 18},
        {"text": "600519", "x": 20, "y": 42, "w": 50, "h": 18},
        {"text": "买入", "x": 95, "y": 43, "w": 30, "h": 18},
        {"text": "已报", "x": 145, "y": 43, "w": 30, "h": 18},
        {"text": "1420.55", "x": 205, "y": 42, "w": 55, "h": 18},
        {"text": "100", "x": 290, "y": 44, "w": 28, "h": 18},
    ]

    rows = ScreenOCR._group_words_into_rows(words)

    assert rows[0] == "证券代码 委托价 数量"
    assert rows[1] == "600519 买入 已报 1420.55 100"

def test_detect_trade_panel_readback_rejects_noise_without_panel_context(monkeypatch):
    ocr = ScreenOCR.__new__(ScreenOCR)

    monkeypatch.setattr(
        ocr,
        "read_text",
        lambda image=None, region=None: {
            "ok": True,
            "text": "audit.py 里只有 600519 和 199，以及普通编辑器文本",
            "lines": [
                "audit.py 里只有 600519 和 199，以及普通编辑器文本",
            ],
            "words": [],
        },
    )

    result = ocr.detect_trade_panel_readback(panel="entrust", stock_code="600519", broker="同花顺")

    assert result["ok"] is True
    assert result["found"] is False
    assert result["rejected_noise"] is True
    assert result["rows"] == []
    assert result["matched_lines"] == []
    assert result["summary"] == {}



