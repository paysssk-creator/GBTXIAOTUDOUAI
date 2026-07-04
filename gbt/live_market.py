"""
live_market.py — 实时行情数据源 (akshare)
支持: A股指数/个股行情/自选股批量/日K线
"""
import akshare as ak
import pandas as pd
import time, logging, threading, json, os
from datetime import datetime
from typing import Dict, List, Optional

L = logging.getLogger("gbt.market")
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_cache.json")


class LiveMarket:
    """实时行情 — 单例"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.cache = {}
        self.last_update = None
        self.cache_ttl = 15  # 15秒缓存
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
        except Exception:
            self.cache = {}

    def _save_cache(self):
        try:
            data = {"last_update": self.last_update, "quotes": self.cache}
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_fresh(self):
        if not self.last_update or not self.cache:
            return False
        return (time.time() - self.last_update) < self.cache_ttl

    def get_indices(self) -> List[Dict]:
        """获取三大指数"""
        try:
            df = ak.stock_zh_index_spot_em()
            indices = []
            targets = {"上证指数": "000001", "深证成指": "399001", "创业板指": "399006"}
            for _, row in df.iterrows():
                name = str(row.get("名称", ""))
                if name in targets:
                    indices.append({
                        "name": name,
                        "code": targets.get(name, ""),
                        "price": float(row.get("最新价", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "change_val": float(row.get("涨跌额", 0)),
                        "volume": float(row.get("成交量", 0)) / 1e8,
                    })
            if indices:
                self.last_update = time.time()
                for idx in indices:
                    self.cache[idx["code"]] = idx
            return indices
        except Exception as e:
            L.warning(f"Index fetch failed: {e}")
            return [n for n in self.cache.values()
                    if n.get("code") in ("000001", "399001", "399006")]

    def get_quote(self, code: str) -> Optional[Dict]:
        """获取个股行情 — akshare实时"""
        # 加市场前缀
        market = "sh" if code.startswith(("6", "5", "9")) else "sz"
        symbol = f"{market}{code}"

        # 先看缓存
        if code in self.cache and self._is_fresh():
            return self.cache[code]

        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            if row.empty:
                L.warning(f"Quote {code} 未在 akshare 实时表内 — 返回 None（严禁 fake）")
                return None
            r = row.iloc[0]
            quote = {
                "code": code,
                "name": str(r.get("名称", "")),
                "price": float(r.get("最新价", 0)),
                "open": float(r.get("今开", 0)),
                "high": float(r.get("最高", 0)),
                "low": float(r.get("最低", 0)),
                "pre_close": float(r.get("昨收", 0)),
                "change_pct": float(r.get("涨跌幅", 0)),
                "change_val": float(r.get("涨跌额", 0)),
                "volume": float(r.get("成交量", 0)) / 1e4,
                "amount": float(r.get("成交额", 0)) / 1e8,
                "turnover": float(r.get("换手率", 0)),
                "pe": float(r.get("市盈率-动态", 0) or 0),
                "pb": float(r.get("市净率", 0) or 0),
                "total_mv": float(r.get("总市值", 0) or 0) / 1e8,
                "updated": time.strftime("%H:%M:%S"),
            }
            self.cache[code] = quote
            self.last_update = time.time()
            self._save_cache()
            return quote
        except Exception as e:
            L.warning(f"Quote fetch {code} failed: {e} — 返回 None（严禁 fake 兜底）")
            return None

    def get_watchlist_quotes(self, watchlist: List[tuple]) -> List[Dict]:
        """批量获取自选股行情"""
        results = []
        for code, name in watchlist:
            q = self.get_quote(code)
            if q:
                results.append(q)
        return results

    def get_daily_kline(self, code: str, days: int = 60) -> List[Dict]:
        """获取日K线 — 主源 akshare → 备用源 Tencent → 严禁 fake 兜底（用户铁律）"""
        market = "sh" if code.startswith(("6", "5", "9")) else "sz"
        symbol = f"{market}{code}"
        # 主源：akshare（前复权）
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is not None and not df.empty:
                klines = []
                for _, r in df.tail(days).iterrows():
                    klines.append({
                        "date": str(r.get("日期", ""))[:10],
                        "open": float(r.get("开盘", 0)),
                        "close": float(r.get("收盘", 0)),
                        "high": float(r.get("最高", 0)),
                        "low": float(r.get("最低", 0)),
                        "volume": float(r.get("成交量", 0)),
                    })
                if klines:
                    return klines
        except Exception as e:
            L.warning(f"akshare get_daily_kline({code}) failed: {e} — falling back to tencent")

        # 备用源：腾讯 web.ifzq.gtimg.cn（稳定，前复权）
        try:
            import urllib.request, json as _json
            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{days},qfq"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = _json.loads(r.read())
            # 腾讯返回结构：{"code":0,"data":{"sh601318":{"qfqday":[[date,open,close,high,low,volume,...], ...]}}}
            data_block = raw.get("data", {}).get(symbol, {})
            klines_raw = data_block.get("qfqday") or data_block.get("day") or []
            if klines_raw:
                klines = []
                for row in klines_raw:
                    if len(row) >= 6:
                        klines.append({
                            "date": str(row[0])[:10],
                            "open": float(row[1] or 0),
                            "close": float(row[2] or 0),
                            "high": float(row[3] or 0),
                            "low": float(row[4] or 0),
                            "volume": float(row[5] or 0),
                        })
                if klines:
                    L.info(f"tencent get_daily_kline({code}) OK · {len(klines)} bars")
                    return klines
        except Exception as e:
            L.warning(f"tencent get_daily_kline({code}) failed: {e}")

        # 双源都失败：严禁 fake K线（用户铁律） — 返回空 list
        L.error(f"get_daily_kline({code}) 双源都失败，已禁用 fake K线兜底")
        return []

    def _mock_klines(self, code, days=60):
        """兼容旧接口 · 严禁 fake K线（用户铁律）
        返回空 list + ERROR 日志；调用方应改用 gbt.connectors.market + 第三方接口拿真数据
        """
        L.error(f"_mock_klines({code}, {days}) called — 已禁用 fake K线，请改用 gbt.connectors.market")
        return []

    def _mock_quote(self, code):
        """兼容旧接口 · 严禁任何 fake / mock 数据（用户铁律）
        直接返回 None + WARNING 日志；调用方应改用 gbt.connectors.market.get_stock() 拿真数据
        """
        L.error(f"_mock_quote({code}) called — 已禁用 fake 数据，请改用 gbt.connectors.market.get_stock()")
        return None


# 全局单例
_market = None


def get_market() -> LiveMarket:
    global _market
    if _market is None:
        _market = LiveMarket()
    return _market
