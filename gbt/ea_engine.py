# -*- coding: utf-8 -*-
"""
ea_engine.py — EA-style quantitative A-share trading engine

Small-position core strategy with:
- Position sizing / lot addition modes
- Profit pyramiding (盈利加仓)
- Loss DCA / Martingale (亏损加仓)
- ATR-based spacing
- Multiplier modes
- Stop-loss / take-profit

All decisions respect A-share rules:
- Lot size: 100 shares
- T+1 settlement
- Daily price limit ±10% / ±20% / ±30% by board
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from gbt.a_share_rules import AShareRuleEngine, Board, a_share

L = logging.getLogger("GBT.EA")


class AddMode(Enum):
    """加仓手数模式"""
    HALF_MULTIPLIER = "half_multiplier"      # /2 加仓倍数：每次加仓是前一次的 1/2
    INCREMENT_LOTS = "increment_lots"        # /2 递增手数：每次固定增加 N 手
    CUSTOM_LOTS = "custom_lots"              # b 加仓自定义手数
    ORDER_COEFFICIENT = "order_coefficient"  # 1/2 按单数加仓系数


class IntervalMode(Enum):
    """加仓间隔模式"""
    FIXED = "fixed"                          # 固定间隔
    CUSTOM = "custom"                        # 自定义间隔序列
    ATR = "atr"                              # ATR 倍数间隔


class MultiplierMode(Enum):
    """倍数模式"""
    FIXED_1_0 = "1.0"                        # 固定 1.0 (默认无放大)
    FIXED_1_1 = "1.1"                        # 固定 1.1
    FIXED_0_01 = "0.01"                      # 固定 0.01
    SEQUENCE = "sequence"                    # 自定义序列


@dataclass
class EAConfig:
    """EA 小仓位核心策略配置"""

    # 初始仓位
    base_lots: int = 1                       # 初始手数 (1手 = 100股)

    # 加仓手数模式
    add_mode: AddMode = AddMode.HALF_MULTIPLIER
    increment_lots: int = 1                  # /2 递增手数 每次增加 N 手
    custom_lots_sequence: List[int] = field(default_factory=lambda: [1, 1, 2, 2, 2, 3, 3, 3, 4])
    order_coefficient: float = 0.5           # 按单数加仓系数

    # 盈利加仓
    profit_add_enabled: bool = True
    profit_interval_mode: IntervalMode = IntervalMode.FIXED
    profit_fixed_spacing: float = 1.00       # 固定间隔 (元)
    profit_custom_intervals: List[float] = field(default_factory=lambda: [1.0] * 14)
    profit_atr_period: int = 14
    profit_atr_multiplier: float = 1.0

    # 亏损加仓
    loss_add_enabled: bool = True
    loss_interval_mode: IntervalMode = IntervalMode.FIXED
    loss_fixed_spacing: float = 1.00         # 固定间隔 (元)
    loss_custom_intervals: List[float] = field(default_factory=lambda: [1.0] * 14)
    loss_atr_period: int = 14
    loss_atr_multiplier: float = 1.0

    # 倍数模式
    multiplier_mode: MultiplierMode = MultiplierMode.FIXED_1_0
    multiplier_sequence: List[float] = field(
        default_factory=lambda: [0.01, 0.01, 0.02, 0.02, 0.02, 0.03, 0.03, 0.03, 0.04]
    )

    # 止损/止盈
    stop_loss_points: float = 200.0          # 止损点数 (1点 = 0.01元)
    take_profit_points: float = 200.0        # 止盈点数 (1点 = 0.01元)
    use_avg_price_tp: bool = True            # 1/2 均价止盈点数

    # 风控
    max_total_additions: int = 10            # 最大加仓次数
    max_position_lots: int = 20              # 最大持仓手数
    daily_loss_limit_pct: float = 5.0        # 当日最大亏损 %

    def to_dict(self) -> Dict:
        return {
            "base_lots": self.base_lots,
            "add_mode": self.add_mode.value,
            "increment_lots": self.increment_lots,
            "custom_lots_sequence": list(self.custom_lots_sequence),
            "order_coefficient": self.order_coefficient,
            "profit_add_enabled": self.profit_add_enabled,
            "profit_interval_mode": self.profit_interval_mode.value,
            "profit_fixed_spacing": self.profit_fixed_spacing,
            "profit_custom_intervals": list(self.profit_custom_intervals),
            "profit_atr_period": self.profit_atr_period,
            "profit_atr_multiplier": self.profit_atr_multiplier,
            "loss_add_enabled": self.loss_add_enabled,
            "loss_interval_mode": self.loss_interval_mode.value,
            "loss_fixed_spacing": self.loss_fixed_spacing,
            "loss_custom_intervals": list(self.loss_custom_intervals),
            "loss_atr_period": self.loss_atr_period,
            "loss_atr_multiplier": self.loss_atr_multiplier,
            "multiplier_mode": self.multiplier_mode.value,
            "multiplier_sequence": list(self.multiplier_sequence),
            "stop_loss_points": self.stop_loss_points,
            "take_profit_points": self.take_profit_points,
            "use_avg_price_tp": self.use_avg_price_tp,
            "max_total_additions": self.max_total_additions,
            "max_position_lots": self.max_position_lots,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "EAConfig":
        def _enum(ecls, val):
            try:
                return ecls(val)
            except Exception:
                return list(ecls)[0]

        return cls(
            base_lots=int(d.get("base_lots", 1)),
            add_mode=_enum(AddMode, d.get("add_mode", "half_multiplier")),
            increment_lots=int(d.get("increment_lots", 1)),
            custom_lots_sequence=list(d.get("custom_lots_sequence", [1, 1, 2, 2, 2, 3, 3, 3, 4])),
            order_coefficient=float(d.get("order_coefficient", 0.5)),
            profit_add_enabled=bool(d.get("profit_add_enabled", True)),
            profit_interval_mode=_enum(IntervalMode, d.get("profit_interval_mode", "fixed")),
            profit_fixed_spacing=float(d.get("profit_fixed_spacing", 1.0)),
            profit_custom_intervals=list(d.get("profit_custom_intervals", [1.0] * 14)),
            profit_atr_period=int(d.get("profit_atr_period", 14)),
            profit_atr_multiplier=float(d.get("profit_atr_multiplier", 1.0)),
            loss_add_enabled=bool(d.get("loss_add_enabled", True)),
            loss_interval_mode=_enum(IntervalMode, d.get("loss_interval_mode", "fixed")),
            loss_fixed_spacing=float(d.get("loss_fixed_spacing", 1.0)),
            loss_custom_intervals=list(d.get("loss_custom_intervals", [1.0] * 14)),
            loss_atr_period=int(d.get("loss_atr_period", 14)),
            loss_atr_multiplier=float(d.get("loss_atr_multiplier", 1.0)),
            multiplier_mode=_enum(MultiplierMode, d.get("multiplier_mode", "1.0")),
            multiplier_sequence=list(d.get("multiplier_sequence", [0.01, 0.01, 0.02, 0.02, 0.02, 0.03, 0.03, 0.03, 0.04])),
            stop_loss_points=float(d.get("stop_loss_points", 100.0)),
            take_profit_points=float(d.get("take_profit_points", 100.0)),
            use_avg_price_tp=bool(d.get("use_avg_price_tp", True)),
            max_total_additions=int(d.get("max_total_additions", 10)),
            max_position_lots=int(d.get("max_position_lots", 20)),
            daily_loss_limit_pct=float(d.get("daily_loss_limit_pct", 5.0)),
        )


@dataclass
class PositionSnapshot:
    """持仓快照"""
    code: str
    name: str = ""
    total_shares: int = 0                  # 总股数
    avg_cost: float = 0.0                  # 均价
    additions: int = 0                     # 已加仓次数
    initial_price: float = 0.0             # 首笔价格
    highest_price: float = 0.0             # 持仓最高价（移动止损用）
    lowest_price: float = 0.0              # 持仓最低价
    last_add_price: float = 0.0            # 上一次加仓价格
    buy_orders: List[Dict] = field(default_factory=list)

    @property
    def total_lots(self) -> int:
        return self.total_shares // 100

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.avg_cost) * self.total_shares

    def unrealized_pnl_pct(self, price: float) -> float:
        if self.avg_cost <= 0:
            return 0.0
        return (price - self.avg_cost) / self.avg_cost * 100


@dataclass
class EADecision:
    """EA 决策结果"""
    action: str                            # open / add_profit / add_loss / close / hold
    code: str
    shares: int
    price: float
    reason: str
    stop_loss: float = 0.0
    take_profit: float = 0.0
    addition_index: int = 0                # 第几次加仓 (0=建仓)
    confidence: float = 0.0


class EAEngine:
    """EA 量化交易引擎"""

    def __init__(self, config: Optional[EAConfig] = None, rule_engine: Optional[AShareRuleEngine] = None):
        self.cfg = config or EAConfig()
        self.rules = rule_engine or a_share

    # ═══════════════════════════════════════════════════
    # 工具函数
    # ═══════════════════════════════════════════════════
    @staticmethod
    def calculate_atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
        """计算 Average True Range"""
        if len(closes) < period + 1:
            return 0.0
        trs: List[float] = []
        for i in range(1, len(closes)):
            h, l, c_prev = highs[i], lows[i], closes[i - 1]
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            trs.append(tr)
        if len(trs) < period:
            return 0.0
        return sum(trs[-period:]) / period

    @staticmethod
    def points_to_price(points: float) -> float:
        """点数 -> 价格差 (A股 1点 = 0.01元)"""
        return points * 0.01

    @staticmethod
    def round_to_lot(shares: int) -> int:
        """A股 100股整数倍"""
        return max(0, (shares // 100) * 100)

    # ═══════════════════════════════════════════════════
    # 仓位 / 手数计算
    # ═══════════════════════════════════════════════════
    def initial_shares(self) -> int:
        """初始建仓股数"""
        return self.round_to_lot(self.cfg.base_lots * 100)

    def _multiplier_for_index(self, index: int) -> float:
        """获取第 index 次加仓的倍数"""
        if self.cfg.multiplier_mode == MultiplierMode.FIXED_1_0:
            return 1.0
        if self.cfg.multiplier_mode == MultiplierMode.FIXED_1_1:
            return 1.1
        if self.cfg.multiplier_mode == MultiplierMode.FIXED_0_01:
            return 0.01
        seq = self.cfg.multiplier_sequence
        if seq:
            return float(seq[index % len(seq)])
        return 1.0

    def addition_lots(self, addition_index: int) -> int:
        """计算第 addition_index 次加仓应加多少手 (从1开始)"""
        idx = addition_index - 1  # 转为 0-based
        if self.cfg.add_mode == AddMode.HALF_MULTIPLIER:
            # 每次是前一次的 1/2，首笔 = base_lots
            lots = max(1, int(round(self.cfg.base_lots * (0.5 ** idx))))
        elif self.cfg.add_mode == AddMode.INCREMENT_LOTS:
            lots = self.cfg.base_lots + idx * self.cfg.increment_lots
        elif self.cfg.add_mode == AddMode.CUSTOM_LOTS:
            seq = self.cfg.custom_lots_sequence
            lots = int(seq[idx % len(seq)]) if seq else self.cfg.base_lots
        elif self.cfg.add_mode == AddMode.ORDER_COEFFICIENT:
            lots = max(1, int(round(self.cfg.base_lots * (1 + idx * self.cfg.order_coefficient))))
        else:
            lots = self.cfg.base_lots

        # 叠加倍数模式
        lots = max(1, int(round(lots * self._multiplier_for_index(idx))))
        return min(lots, self.cfg.max_position_lots)

    def addition_shares(self, addition_index: int) -> int:
        return self.round_to_lot(self.addition_lots(addition_index) * 100)

    # ═══════════════════════════════════════════════════
    # 加仓间隔计算
    # ═══════════════════════════════════════════════════
    def _spacing(
        self,
        mode: IntervalMode,
        fixed: float,
        custom: Sequence[float],
        atr_period: int,
        atr_multiplier: float,
        addition_index: int,
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
        closes: Optional[Sequence[float]] = None,
    ) -> float:
        """计算加仓间隔（价格差，单位：元）"""
        idx = addition_index - 1
        if mode == IntervalMode.FIXED:
            return fixed
        if mode == IntervalMode.CUSTOM:
            seq = list(custom) if custom else [fixed]
            return float(seq[idx % len(seq)])
        if mode == IntervalMode.ATR:
            atr = self.calculate_atr(highs or [], lows or [], closes or [], atr_period)
            return atr * atr_multiplier
        return fixed

    def profit_spacing(
        self,
        addition_index: int,
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
        closes: Optional[Sequence[float]] = None,
    ) -> float:
        return self._spacing(
            self.cfg.profit_interval_mode,
            self.cfg.profit_fixed_spacing,
            self.cfg.profit_custom_intervals,
            self.cfg.profit_atr_period,
            self.cfg.profit_atr_multiplier,
            addition_index,
            highs, lows, closes,
        )

    def loss_spacing(
        self,
        addition_index: int,
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
        closes: Optional[Sequence[float]] = None,
    ) -> float:
        return self._spacing(
            self.cfg.loss_interval_mode,
            self.cfg.loss_fixed_spacing,
            self.cfg.loss_custom_intervals,
            self.cfg.loss_atr_period,
            self.cfg.loss_atr_multiplier,
            addition_index,
            highs, lows, closes,
        )

    # ═══════════════════════════════════════════════════
    # 止损 / 止盈
    # ═══════════════════════════════════════════════════
    def stop_loss_price(self, avg_cost: float, long: bool = True) -> float:
        """止损价"""
        sl = self.points_to_price(self.cfg.stop_loss_points)
        return round(avg_cost - sl, 2) if long else round(avg_cost + sl, 2)

    def take_profit_price(self, avg_cost: float, long: bool = True) -> float:
        """止盈价"""
        tp = self.points_to_price(self.cfg.take_profit_points)
        return round(avg_cost + tp, 2) if long else round(avg_cost - tp, 2)

    # ═══════════════════════════════════════════════════
    # 核心决策
    # ═══════════════════════════════════════════════════
    def decide(
        self,
        code: str,
        price: float,
        signal: str,                          # buy / sell / hold
        position: Optional[PositionSnapshot] = None,
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
        closes: Optional[Sequence[float]] = None,
        name: str = "",
    ) -> EADecision:
        """
        根据当前价格、信号、持仓，返回 EA 决策。
        """
        signal = signal.lower()
        if signal not in ("buy", "sell", "hold"):
            signal = "hold"

        # 无持仓 -> 建仓
        if position is None or position.total_shares == 0:
            if signal == "buy":
                shares = self.initial_shares()
                sl = self.stop_loss_price(price, long=True)
                tp = self.take_profit_price(price, long=True)
                return EADecision(
                    action="open", code=code, shares=shares, price=round(price, 2),
                    reason="首次建仓 (做多)", stop_loss=sl, take_profit=tp,
                    addition_index=0, confidence=70.0,
                )
            if signal == "sell":
                # A股 T+1，空仓无法做空，忽略 sell
                return EADecision(action="hold", code=code, shares=0, price=round(price, 2),
                                  reason="空仓，忽略做空信号 (A股 T+1)")
            return EADecision(action="hold", code=code, shares=0, price=round(price, 2),
                              reason="无信号，观望")

        # 有持仓 -> 检查止损止盈 / 加仓 / 平仓
        pos = position
        long_position = pos.total_shares > 0

        # 止损检查
        sl_price = self.stop_loss_price(pos.avg_cost, long=long_position)
        if long_position and price <= sl_price:
            return EADecision(
                action="close", code=code, shares=pos.total_shares, price=round(price, 2),
                reason=f"止损触发: 价格{price} <= 止损价{sl_price}",
                stop_loss=sl_price, take_profit=self.take_profit_price(pos.avg_cost, long=True),
                addition_index=pos.additions, confidence=95.0,
            )

        # 止盈检查
        tp_price = self.take_profit_price(pos.avg_cost, long=long_position)
        if long_position and price >= tp_price:
            return EADecision(
                action="close", code=code, shares=pos.total_shares, price=round(price, 2),
                reason=f"止盈触发: 价格{price} >= 止盈价{tp_price}",
                stop_loss=sl_price, take_profit=tp_price,
                addition_index=pos.additions, confidence=95.0,
            )

        # 加仓次数已达上限
        if pos.additions >= self.cfg.max_total_additions:
            return EADecision(
                action="hold", code=code, shares=0, price=round(price, 2),
                reason=f"已达最大加仓次数 {self.cfg.max_total_additions}",
                stop_loss=sl_price, take_profit=tp_price,
            )

        next_idx = pos.additions + 1
        max_lots = self.cfg.max_position_lots
        if pos.total_lots >= max_lots:
            return EADecision(
                action="hold", code=code, shares=0, price=round(price, 2),
                reason=f"已达最大持仓手数 {max_lots}",
                stop_loss=sl_price, take_profit=tp_price,
            )

        # 盈利加仓
        if self.cfg.profit_add_enabled and signal == "buy" and price > pos.avg_cost:
            spacing = self.profit_spacing(next_idx, highs, lows, closes)
            target = pos.last_add_price if pos.last_add_price > 0 else pos.avg_cost
            if price >= target + spacing:
                shares = self.addition_shares(next_idx)
                if shares > 0:
                    return EADecision(
                        action="add_profit", code=code, shares=shares, price=round(price, 2),
                        reason=f"盈利加仓 #{next_idx}: 价格{price} >= 基准{target:.2f} + 间隔{spacing:.2f}",
                        stop_loss=sl_price, take_profit=tp_price,
                        addition_index=next_idx, confidence=75.0,
                    )

        # 亏损加仓 (DCA)
        if self.cfg.loss_add_enabled and signal == "buy" and price < pos.avg_cost:
            spacing = self.loss_spacing(next_idx, highs, lows, closes)
            target = pos.last_add_price if pos.last_add_price > 0 else pos.avg_cost
            if price <= target - spacing:
                shares = self.addition_shares(next_idx)
                if shares > 0:
                    return EADecision(
                        action="add_loss", code=code, shares=shares, price=round(price, 2),
                        reason=f"亏损加仓 #{next_idx}: 价格{price} <= 基准{target:.2f} - 间隔{spacing:.2f}",
                        stop_loss=sl_price, take_profit=tp_price,
                        addition_index=next_idx, confidence=60.0,
                    )

        # 卖出信号平仓
        if signal == "sell":
            return EADecision(
                action="close", code=code, shares=pos.total_shares, price=round(price, 2),
                reason="策略卖出信号", stop_loss=sl_price, take_profit=tp_price,
                addition_index=pos.additions, confidence=80.0,
            )

        return EADecision(
            action="hold", code=code, shares=0, price=round(price, 2),
            reason="持仓中，未触发加/减仓条件", stop_loss=sl_price, take_profit=tp_price,
            addition_index=pos.additions,
        )

    # ═══════════════════════════════════════════════════
    # 更新持仓快照
    # ═══════════════════════════════════════════════════
    def apply_fill(
        self,
        position: Optional[PositionSnapshot],
        decision: EADecision,
        fee_rate: float = 0.0003,
    ) -> PositionSnapshot:
        """根据成交决策更新持仓快照（简化，不含现金检查）"""
        if decision.action == "hold":
            return position or PositionSnapshot(code=decision.code)

        if decision.action == "close":
            return PositionSnapshot(code=decision.code)

        # open / add_profit / add_loss
        if position is None or position.total_shares == 0:
            pos = PositionSnapshot(
                code=decision.code,
                total_shares=decision.shares,
                avg_cost=decision.price,
                additions=0,
                initial_price=decision.price,
                highest_price=decision.price,
                lowest_price=decision.price,
                last_add_price=decision.price,
            )
        else:
            pos = position
            old_cost = pos.total_shares * pos.avg_cost
            new_cost = decision.shares * decision.price
            total = pos.total_shares + decision.shares
            pos.total_shares = total
            pos.avg_cost = round((old_cost + new_cost) / total, 3) if total > 0 else 0
            pos.additions += 1
            pos.last_add_price = decision.price
            pos.highest_price = max(pos.highest_price, decision.price)
            pos.lowest_price = min(pos.lowest_price, decision.price)
        return pos

    # ═══════════════════════════════════════════════════
    # 合规检查
    # ═══════════════════════════════════════════════════
    def validate_decision(
        self,
        decision: EADecision,
        available_cash: float,
        daily_pnl: float = 0.0,
        board: Board = Board.MAIN,
        prev_close: float = 0.0,
    ) -> Tuple[bool, str]:
        """检查决策是否符合 A股规则与风控"""
        if decision.action == "hold":
            return True, ""

        # 日亏损上限
        if abs(daily_pnl) >= self.cfg.daily_loss_limit_pct:
            return False, f"日亏损已达 {self.cfg.daily_loss_limit_pct}% 上限"

        # 买入必须 100 股整数倍
        if decision.action in ("open", "add_profit", "add_loss"):
            if decision.shares % 100 != 0 or decision.shares <= 0:
                return False, f"买入股数 {decision.shares} 不是 100 整数倍"
            cost = decision.shares * decision.price
            if available_cash < cost:
                return False, f"现金不足: 需要 {cost:.2f}, 可用 {available_cash:.2f}"
            # 涨跌停检查
            if prev_close > 0:
                limit_pct = a_share.limit_up_down_pct(board)
                limit_up = round(prev_close * (1 + limit_pct / 100), 2)
                limit_down = round(prev_close * (1 - limit_pct / 100), 2)
                if decision.price > limit_up:
                    return False, f"买入价 {decision.price} 超过涨停价 {limit_up}"
                if decision.price < limit_down:
                    return False, f"买入价 {decision.price} 低于跌停价 {limit_down}"

        return True, ""
