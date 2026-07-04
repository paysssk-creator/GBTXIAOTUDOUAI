"""
broker_bridge.py — 券商接口骨架 (华泰/中信/雪球)
真实券商API接入层 — 需实际开户后配置
"""
import os, json, time, logging
from typing import Dict, Optional, Any

L = logging.getLogger("gbt.broker")


class BrokerBridge:
    """券商API桥接层"""
    def __init__(self, broker="simulate"):
        self.broker = broker
        self.connected = False
        self.config = self._load_config()

    def _load_config(self):
        env = os.environ
        return {
            "ht_username": env.get("HT_USERNAME", ""),
            "ht_password": env.get("HT_PASSWORD", ""),
            "ht_account": env.get("HT_ACCOUNT", ""),
            "xq_cookie": env.get("XQ_COOKIE", ""),
        }

    def connect(self):
        """连接券商"""
        if self.broker == "simulate":
            self.connected = True
            self.account_id = "SIM-001"
            return {"ok": True, "broker": "模拟交易"}

        if self.broker == "ht":
            try:
                # 华泰 XTP / 恒生接口
                # from xtp import XTPAPI  ← 需实际安装华泰SDK
                return {"ok": False, "error": "华泰SDK未安装 — 请配置xtp模块"}
            except ImportError:
                return {"ok": False, "error": "XTP SDK not installed"}

        if self.broker == "xq":
            if not self.config.get("xq_cookie"):
                return {"ok": False, "error": "雪球Cookie未配置"}
            # SnowballTrade(cookie=xq_cookie)
            return {"ok": False, "error": "雪球API待集成"}

        return {"ok": False, "error": f"未知券商: {self.broker}"}

    def get_balance(self):
        return {"cash": 100000, "total": 100000, "frozen": 0}

    def get_positions(self):
        return []

    def buy(self, code, price, volume):
        if self.broker == "simulate":
            from gbt.paper_account import place_order
            name = {"600519": "贵州茅台", "600036": "招商银行", "000001": "平安银行",
                    "000858": "五粮液", "601318": "中国平安"}.get(code, code)
            return place_order(code, name, "BUY", price, volume)
        return {"ok": False, "error": "真实券商需开通"}

    def sell(self, code, price, volume):
        if self.broker == "simulate":
            from gbt.paper_account import place_order
            name = {"600519": "贵州茅台"}.get(code, code)
            return place_order(code, name, "SELL", price, volume)
        return {"ok": False, "error": "真实券商需开通"}

    def cancel_order(self, order_id):
        return {"ok": False, "error": "暂不支持撤单"}


# 全局单例
_broker = None


def get_broker(broker="simulate") -> BrokerBridge:
    global _broker
    if _broker is None:
        _broker = BrokerBridge(broker=broker)
    return _broker
