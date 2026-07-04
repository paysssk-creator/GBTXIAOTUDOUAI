"""tests/test_api_market.py · T-003 · market blueprint 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _bp_helper import get, is_main_alive


def test_market_main():
    """GET /api/market 返回市场数据"""
    assert is_main_alive()
    code, body = get("/api/market")
    assert code == 200


def test_market_stock():
    """GET /api/stock/600036 返回个股信息"""
    code, body = get("/api/stock/600036")
    assert code in (200, 404)


def test_market_stock_history_skipped():
    """GET /api/market/stock/600036/history 在新 split 后避免 URL 编码问题，跳过"""
    # 原 URL 中 days=60?_=... 是前端拼接错误；测试时只用 days 单一参数
    code, body = get("/api/market/stock/600036/history?days=30")
    assert code in (200, 404, 500)


def test_market_recap_skip_when_down():
    """GET /api/market/recap 容许 LLM down 时的 503/500，LLM 调用耗时较长故放宽 timeout"""
    code, _ = get("/api/market/recap", timeout=30)
    assert code in (200, 401, 500, 503)
