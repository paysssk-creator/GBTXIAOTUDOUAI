# -*- coding: utf-8 -*-
"""
A股交易规则引擎 — 将专业知识编码为可执行约束

覆盖：
- 交易时段 (集合竞价/连续竞价)
- T+1 交收 (当日买入次日才能卖出)
- 涨跌停板 (主板10%、科创/创业板20%、北交所30%、ST*5%)
- 交易单位 (100股/手，整数倍)
- 交易费用 (佣金、印花税、过户费)
- 板块判定与规则查询
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Board(Enum):
    """A股板块分类"""
    MAIN = "main"           # 沪深主板
    STAR = "star"           # 科创板 (sh688)
    CHINEXT = "chinext"     # 创业板 (sz300)
    BSE = "bse"             # 北京证券交易所 (bj)
    ST = "st"               # ST/*ST (按名称或代码前缀判定，优先)


# 涨跌停幅度 (%)
LIMIT_UP_DOWN_PCT: Dict[Board, float] = {
    Board.MAIN: 10.0,
    Board.STAR: 20.0,
    Board.CHINEXT: 20.0,
    Board.BSE: 30.0,
    Board.ST: 5.0,
}

# 交易费用默认参数
DEFAULT_COMMISSION_RATE = 0.00025   # 万2.5
DEFAULT_STAMP_TAX_RATE = 0.0005     # 0.05% 卖出单向
DEFAULT_TRANSFER_FEE_RATE = 0.00001 # 0.001% 双向 (沪市A股，深市免收)
MIN_COMMISSION = 5.0                # 最低佣金5元


@dataclass
class AShareTrade:
    """一笔A股交易记录"""
    code: str
    action: str                       # buy / sell
    shares: int
    price: float
    time: datetime = field(default_factory=datetime.now)
    board: Board = Board.MAIN
    commission: float = 0.0
    stamp_tax: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0           # 买入总支出 / 卖出净收入


@dataclass
class TradeCheckResult:
    """交易合规检查结果"""
    ok: bool
    reason: str = ""
    adjusted_shares: int = 0
    adjusted_price: float = 0.0
    fees: Dict[str, float] = field(default_factory=dict)


class AShareRuleEngine:
    """A股规则引擎：可独立使用，也可注入 Account / Trader"""

    def __init__(
        self,
        commission_rate: float = DEFAULT_COMMISSION_RATE,
        stamp_tax_rate: float = DEFAULT_STAMP_TAX_RATE,
        transfer_fee_rate: float = DEFAULT_TRANSFER_FEE_RATE,
        min_commission: float = MIN_COMMISSION,
    ):
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.min_commission = min_commission

    # ── 板块判定 ──
    @staticmethod
    def detect_board(code: str, name: str = "") -> Board:
        """根据股票代码/名称判定板块"""
        code = code.lower().strip()
        name = name.upper()
        if "ST" in name or "*ST" in name:
            return Board.ST
        if code.startswith("sh688"):
            return Board.STAR
        if code.startswith("sz300"):
            return Board.CHINEXT
        if code.startswith("bj") or code.startswith("sh8") or code.startswith("sz8"):
            return Board.BSE
        return Board.MAIN

    @staticmethod
    def is_index(code: str) -> bool:
        """判定是否为指数代码"""
        c = code.lower()
        return c.startswith("sh000") or c.startswith("sz399") or c.startswith("bj899")

    # ── 涨跌停 ──
    def limit_pct(self, code: str, name: str = "") -> float:
        """返回该股涨跌停幅度 (%)"""
        return LIMIT_UP_DOWN_PCT[self.detect_board(code, name)]

    def limit_prices(self, code: str, prev_close: float, name: str = "") -> Tuple[float, float]:
        """根据昨收计算今日涨跌停价"""
        if prev_close <= 0:
            return 0.0, 0.0
        pct = self.limit_pct(code, name) / 100.0
        limit_up = round(prev_close * (1 + pct), 2)
        limit_down = round(prev_close * (1 - pct), 2)
        return limit_up, limit_down

    def price_in_limit(self, code: str, price: float, prev_close: float, name: str = "") -> bool:
        """价格是否在涨跌停范围内"""
        if prev_close <= 0:
            return True
        up, down = self.limit_prices(code, prev_close, name)
        return down <= price <= up

    # ── 交易单位 ──
    @staticmethod
    def normalize_lot(shares: int) -> int:
        """将股数规整为100的整数倍，向下取整"""
        return max(0, (int(shares) // 100) * 100)

    @staticmethod
    def validate_lot(shares: int) -> Tuple[bool, str]:
        """检查股数是否符合A股交易单位"""
        if shares <= 0:
            return False, "交易数量必须大于0"
        if shares % 100 != 0:
            return False, f"A股交易单位为100股整数倍，当前{shares}股"
        return True, ""

    # ── 交易时段 ──
    @staticmethod
    def is_trading_time(dt: Optional[datetime] = None) -> bool:
        """是否为A股连续竞价交易时段 (不含集合竞价)"""
        dt = dt or datetime.now()
        t = dt.time()
        weekday = dt.weekday()
        if weekday >= 5:  # 周末休市
            return False
        morning = time(9, 30) <= t <= time(11, 30)
        afternoon = time(13, 0) <= t <= time(15, 0)
        return morning or afternoon

    @staticmethod
    def is_call_auction_time(dt: Optional[datetime] = None) -> bool:
        """是否为开盘集合竞价时段 (9:15-9:25)"""
        dt = dt or datetime.now()
        t = dt.time()
        weekday = dt.weekday()
        if weekday >= 5:
            return False
        return time(9, 15) <= t <= time(9, 25)

    @staticmethod
    def next_trading_day(date: datetime) -> datetime:
        """获取下一个交易日（简化：仅跳过周末）"""
        d = date + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d

    # ── T+1 交收 ──
    @staticmethod
    def can_sell_today(buy_date: datetime, sell_date: datetime) -> bool:
        """判断买入股票在 sell_date 当天是否可卖出"""
        return sell_date.date() > buy_date.date()

    # ── 费用计算 ──
    def calc_buy_fees(self, amount: float, code: str = "") -> Dict[str, float]:
        """计算买入费用"""
        commission = max(amount * self.commission_rate, self.min_commission)
        transfer = amount * self.transfer_fee_rate if code.lower().startswith("sh") else 0.0
        return {
            "commission": round(commission, 2),
            "stamp_tax": 0.0,
            "transfer_fee": round(transfer, 2),
            "total": round(commission + transfer, 2),
        }

    def calc_sell_fees(self, amount: float, code: str = "") -> Dict[str, float]:
        """计算卖出费用 (含印花税)"""
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_tax = amount * self.stamp_tax_rate
        transfer = amount * self.transfer_fee_rate if code.lower().startswith("sh") else 0.0
        return {
            "commission": round(commission, 2),
            "stamp_tax": round(stamp_tax, 2),
            "transfer_fee": round(transfer, 2),
            "total": round(commission + stamp_tax + transfer, 2),
        }

    def check_buy(
        self,
        code: str,
        shares: int,
        price: float,
        prev_close: float,
        available_cash: float,
        name: str = "",
    ) -> TradeCheckResult:
        """买入合规检查"""
        # 交易单位
        normalized = self.normalize_lot(shares)
        if normalized <= 0:
            return TradeCheckResult(False, "买入数量不足1手(100股)")
        if normalized != shares:
            return TradeCheckResult(
                False,
                f"A股买入必须为100股整数倍，已规整为{normalized}股，请确认",
                adjusted_shares=normalized,
                adjusted_price=price,
            )

        # 涨跌停
        if prev_close > 0 and not self.price_in_limit(code, price, prev_close, name):
            up, down = self.limit_prices(code, prev_close, name)
            return TradeCheckResult(
                False,
                f"委托价{price}超出涨跌停范围 [{down}, {up}]",
                adjusted_shares=shares,
                adjusted_price=price,
            )

        # 资金
        amount = shares * price
        fees = self.calc_buy_fees(amount, code)
        total_cost = amount + fees["total"]
        if total_cost > available_cash:
            max_shares = self.normalize_lot((available_cash - fees["total"]) / max(price, 0.01))
            return TradeCheckResult(
                False,
                f"资金不足：需要{total_cost:.2f}，可用{available_cash:.2f}，最多可买{max_shares}股",
                adjusted_shares=max_shares,
                adjusted_price=price,
                fees=fees,
            )

        return TradeCheckResult(
            True,
            "买入检查通过",
            adjusted_shares=shares,
            adjusted_price=price,
            fees=fees,
        )

    def check_sell(
        self,
        code: str,
        shares: int,
        price: float,
        prev_close: float,
        available_shares: int,
        buy_date: Optional[datetime] = None,
        sell_date: Optional[datetime] = None,
        name: str = "",
    ) -> TradeCheckResult:
        """卖出合规检查"""
        normalized = self.normalize_lot(shares)
        if normalized <= 0:
            return TradeCheckResult(False, "卖出数量不足1手(100股)")
        if normalized != shares:
            return TradeCheckResult(
                False,
                f"A股卖出必须为100股整数倍，已规整为{normalized}股",
                adjusted_shares=normalized,
                adjusted_price=price,
            )

        if available_shares < shares:
            return TradeCheckResult(
                False,
                f"持仓不足：持有{available_shares}股，尝试卖出{shares}股",
                adjusted_shares=self.normalize_lot(available_shares),
                adjusted_price=price,
            )

        if buy_date:
            sell_date = sell_date or datetime.now()
            if not self.can_sell_today(buy_date, sell_date):
                return TradeCheckResult(
                    False,
                    "T+1交收：当日买入的股票次日才能卖出",
                    adjusted_shares=shares,
                    adjusted_price=price,
                )

        if prev_close > 0 and not self.price_in_limit(code, price, prev_close, name):
            up, down = self.limit_prices(code, prev_close, name)
            return TradeCheckResult(
                False,
                f"委托价{price}超出涨跌停范围 [{down}, {up}]",
                adjusted_shares=shares,
                adjusted_price=price,
            )

        amount = shares * price
        fees = self.calc_sell_fees(amount, code)
        return TradeCheckResult(
            True,
            "卖出检查通过",
            adjusted_shares=shares,
            adjusted_price=price,
            fees=fees,
        )


# 全局规则引擎实例
a_share = AShareRuleEngine()


# ── 便捷函数 ──
def board_name(board: Board) -> str:
    names = {
        Board.MAIN: "主板",
        Board.STAR: "科创板",
        Board.CHINEXT: "创业板",
        Board.BSE: "北交所",
        Board.ST: "ST板块",
    }
    return names.get(board, "未知")


def get_rules_summary() -> str:
    """返回A股规则摘要文本，供LLM使用"""
    return """A股市场核心规则:
交易时间: 9:15-9:25集合竞价 9:30-11:30/13:00-15:00连续竞价
T+1: 买入当日不可卖出
涨跌停: 主板10% 科创/创业板20% 北交所30% ST/*ST 5%
交易单位: 1手=100股，委托必须为100股整数倍
费用: 印花税0.05%(卖出单向) 佣金约万2.5(最低5元) 过户费0.001%(沪市)
"""
