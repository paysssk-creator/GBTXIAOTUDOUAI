"""
风控引擎 — 止损止盈 · 仓位管理 · 资金风控
"""
import logging

L = logging.getLogger("GBT.RiskCtrl")


class RiskManager:
    """交易风控"""

    def __init__(self, total_capital=100000):
        self.total_capital = total_capital
        self.max_single_pct = 20       # 单票最多20%仓位
        self.max_total_pct = 80        # 总仓位最多80%
        self.stop_loss_pct = 7         # 止损线7%
        self.stop_profit_pct = 15      # 止盈线15%
        self.trailing_stop_pct = 5     # 移动止损5%
        self.max_daily_trades = 10     # 每日最大交易次数
        self.max_daily_loss_pct = 5    # 当日最大亏损5%
        self.daily_trades = 0
        self.daily_pnl = 0
        self.highs = {}                # 持仓最高价(移动止损用)

    def check_position_size(self, price, current_holdings=0):
        """检查仓位大小是否合规"""
        max_shares = int(self.total_capital * self.max_single_pct / 100 / price / 100) * 100
        max_total_shares = int(self.total_capital * self.max_total_pct / 100 / price / 100) * 100 - current_holdings
        allowed = min(max_shares, max_total_shares)
        return {
            "ok": allowed > 0,
            "max_shares": max(0, allowed),
            "reason": f"单票上限{self.max_single_pct}% 总仓位{self.max_total_pct}%"
        }

    def check_stop_loss(self, code, entry_price, current_price):
        """检查止损"""
        loss_pct = round((entry_price - current_price) / entry_price * 100, 2)
        triggered = loss_pct >= self.stop_loss_pct
        return {
            "triggered": triggered,
            "loss_pct": loss_pct,
            "action": "sell" if triggered else "hold",
            "reason": f"止损{self.stop_loss_pct}%触发" if triggered else "正常"
        }

    def check_stop_profit(self, code, entry_price, current_price, high_price=None):
        """检查止盈 + 移动止损"""
        gain_pct = round((current_price - entry_price) / entry_price * 100, 2)

        # 移动止损
        if high_price is None or high_price < current_price:
            high_price = current_price
        trailing_pct = round((high_price - current_price) / high_price * 100, 2)

        if gain_pct >= self.stop_profit_pct:
            return {"triggered": True, "gain_pct": gain_pct, "action": "sell",
                    "reason": f"止盈{self.stop_profit_pct}%触发 (收益+{gain_pct}%)"}

        if trailing_pct >= self.trailing_stop_pct:
            return {"triggered": True, "gain_pct": gain_pct, "action": "sell",
                    "reason": f"移动止损{self.trailing_stop_pct}%触发 (回撤{trailing_pct}%)"}

        return {"triggered": False, "gain_pct": gain_pct, "action": "hold", "reason": "正常"}

    def check_daily_limit(self):
        """检查每日交易限制"""
        return {
            "trades_left": self.max_daily_trades - self.daily_trades,
            "loss_limit_hit": abs(self.daily_pnl) >= self.total_capital * self.max_daily_loss_pct / 100,
            "can_trade": self.daily_trades < self.max_daily_trades and
                         abs(self.daily_pnl) < self.total_capital * self.max_daily_loss_pct / 100
        }

    def approve_trade(self, signal, positions=None):
        """综合审批交易信号"""
        issues = []
        positions = positions or {}

        # 1. 每日限制
        daily = self.check_daily_limit()
        if not daily["can_trade"]:
            if daily["loss_limit_hit"]:
                issues.append(f"当日亏损超限({self.max_daily_loss_pct}%)")
            else:
                issues.append(f"当日交易次数已满({self.max_daily_trades}次)")

        # 2. 仓位检查
        if signal.action == "buy":
            current_val = sum((p.shares * (p.avg_cost or 0)) for p in positions.values())
            pos_check = self.check_position_size(signal.price, current_val // (signal.price or 1))
            if not pos_check["ok"]:
                issues.append("仓位已达上限")

        # 3. 持仓风控检查
        if signal.action == "sell" and signal.code in positions:
            entry = positions[signal.code].avg_cost if hasattr(positions[signal.code], 'avg_cost') else signal.price
            sl = self.check_stop_loss(signal.code, entry, signal.price)
            sp = self.check_stop_profit(signal.code, entry, signal.price)
            # 卖出信号 + 触发止损  = 强制平仓
            if sl["triggered"]:
                signal.action = "sell"
                signal.reason = f"[风控] {sl['reason']}"
                signal.confidence = 100

        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "action": signal.action,
            "confidence": signal.confidence
        }

    def record_trade(self, pnl=0):
        """记录交易"""
        self.daily_trades += 1
        self.daily_pnl += pnl

    def reset_daily(self):
        """重置每日统计"""
        self.daily_trades = 0
        self.daily_pnl = 0


# 全局风控
risk_mgr = RiskManager(total_capital=100000)
