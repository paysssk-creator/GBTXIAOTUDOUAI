"""
GBT 回测引擎 v1 — 历史数据回放 + 策略验证
支持：日线回测、多策略并行、风控约束、绩效报告
"""
import logging
from datetime import datetime, timedelta
from collections import deque

from gbt.a_share_rules import a_share

L = logging.getLogger("GBT.Backtest")


class BacktestResult:
    """单次回测结果"""
    def __init__(self):
        self.initial_capital = 0
        self.final_equity = 0
        self.total_return = 0
        self.annual_return = 0
        self.max_drawdown = 0
        self.sharpe_ratio = 0
        self.win_rate = 0
        self.total_trades = 0
        self.win_trades = 0
        self.loss_trades = 0
        self.avg_win = 0
        self.avg_loss = 0
        self.profit_factor = 0
        self.equity_curve = []
        self.trade_log = []
        self.signal_stats = {}
        self.monthly_returns = {}
        self.params = {}

    def to_dict(self):
        return {
            "initial_capital": round(self.initial_capital, 2),
            "final_equity": round(self.final_equity, 2),
            "total_return_pct": round(self.total_return, 2),
            "annual_return_pct": round(self.annual_return, 2),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "win_rate_pct": round(self.win_rate, 2),
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "signal_stats": self.signal_stats,
            "monthly_returns": self.monthly_returns,
            "params": self.params,
        }

    def summary(self):
        """人类可读摘要"""
        return f"""
╔══════════════════════════════════════╗
║        📊 回测报告                    ║
╠══════════════════════════════════════╣
║ 初始资金: ¥{self.initial_capital:>12,.0f}      ║
║ 最终权益: ¥{self.final_equity:>12,.0f}      ║
║ 总收益率: {self.total_return:>11.2f}%          ║
║ 年化收益: {self.annual_return:>11.2f}%          ║
║ 最大回撤: {self.max_drawdown:>11.2f}%          ║
║ 夏普比率: {self.sharpe_ratio:>11.2f}            ║
╠══════════════════════════════════════╣
║ 总交易数: {self.total_trades:>11d}              ║
║ 胜率:     {self.win_rate:>11.1f}%              ║
║ 盈利因子: {self.profit_factor:>11.2f}            ║
║ 平均盈利: ¥{self.avg_win:>10,.0f}            ║
║ 平均亏损: ¥{self.avg_loss:>10,.0f}            ║
╚══════════════════════════════════════╝"""


class BacktestEngine:
    """回测引擎 — 在历史数据上重放策略"""

    def __init__(self, db=None):
        self.db = db
        self.initial_capital = 100000
        self.cash = 100000
        self.positions = {}       # {code: {"shares": n, "avg_cost": p}}
        self.trades = []
        self.equity_curve = []
        self._commission_rate = a_share.commission_rate  # 佣金
        self._stamp_tax_rate = a_share.stamp_tax_rate     # 印花税(卖出单向)
        self._transfer_fee_rate = a_share.transfer_fee_rate  # 过户费
        self._min_commission = a_share.min_commission     # 最低佣金

        # 风控参数
        self.stop_loss_pct = 7
        self.stop_profit_pct = 15
        self.max_single_pct = 20
        self.max_daily_trades = 20
        self.confidence_threshold = 60

        # 策略权重
        self.strategy_weights = {}

    def run(self, code, kline_data, strategy_fn=None, start_date=None, end_date=None, **params):
        """
        执行回测
        kline_data: trader.fetch_kline() 的返回值 {closes:[], highs:[], lows:[], volumes:[], raw:[{day,open,close,high,low,volume}]}
        strategy_fn: 选股函数 f(closes, highs, lows, volumes, index) -> {signal: buy/sell/hold, confidence: 0-100}
        start_date/end_date: "YYYY-MM-DD"
        """
        # 应用参数
        for k, v in params.items():
            if hasattr(self, k):
                setattr(self, k, v)

        result = BacktestResult()
        result.initial_capital = self.initial_capital
        result.params = {k: v for k, v in params.items()}

        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()

        raw = kline_data.get("raw", [])
        closes = kline_data.get("closes", [])
        highs = kline_data.get("highs", [])
        lows = kline_data.get("lows", [])
        volumes = kline_data.get("volumes", [])

        if len(closes) < 20:
            result.total_return = 0
            result.final_equity = self.initial_capital
            return result

        # 过滤日期范围
        start_idx = 0
        end_idx = len(raw)
        if start_date:
            for i, d in enumerate(raw):
                if d.get("day", "") >= start_date:
                    start_idx = i
                    break
        if end_date:
            for i in range(len(raw) - 1, -1, -1):
                if raw[i].get("day", "") <= end_date:
                    end_idx = i + 1
                    break

        # 需要一段预热期用于计算技术指标
        warmup = min(20, start_idx)
        start_idx = max(warmup, start_idx)

        daily_equities = []
        daily_trade_count = 0
        daily_date = None

        for i in range(start_idx, end_idx):
            # 切片历史数据到当前位置
            slice_closes = closes[:i + 1]
            slice_highs = highs[:i + 1] if highs else slice_closes
            slice_lows = lows[:i + 1] if lows else slice_closes
            slice_volumes = volumes[:i + 1] if volumes else [0] * (i + 1)

            current_price = closes[i]
            current_day = raw[i].get("day", "")

            # 日统计重置
            if current_day != daily_date:
                daily_trade_count = 0
                daily_date = current_day

            # ── 检查持仓止盈止损 ──
            for pos_code in list(self.positions.keys()):
                pos = self.positions[pos_code]
                entry_price = pos["avg_cost"]
                profit_pct = (current_price - entry_price) / entry_price * 100

                # 止损
                if profit_pct <= -self.stop_loss_pct:
                    shares = pos["shares"]
                    self._close_position(pos_code, current_price, shares, "止损")
                    daily_trade_count += 1
                    continue

                # 止盈
                if profit_pct >= self.stop_profit_pct:
                    shares = pos["shares"]
                    self._close_position(pos_code, current_price, shares, "止盈")
                    daily_trade_count += 1

            # ── 策略信号 ──
            if strategy_fn and daily_trade_count < self.max_daily_trades:
                try:
                    signal = strategy_fn(slice_closes, slice_highs, slice_lows, slice_volumes, i)
                except Exception as e:
                    L.debug(f"策略执行异常 @ {current_day}: {e}")
                    signal = {"signal": "hold", "confidence": 0}

                if signal.get("signal") in ("buy", "sell") and signal.get("confidence", 0) >= self.confidence_threshold:
                    # 仓位检查
                    if signal["signal"] == "buy" and code not in self.positions:
                        max_cost = self.cash * self.max_single_pct / 100
                        shares = int(max_cost / max(current_price, 0.01) / 100) * 100
                        if shares >= 100:
                            self._open_position(code, current_price, shares)
                            daily_trade_count += 1
                            self.trades[-1]["signal"] = signal.get("reason", "")

                    elif signal["signal"] == "sell" and code in self.positions:
                        pos = self.positions[code]
                        self._close_position(code, current_price, pos["shares"], "信号卖出")
                        daily_trade_count += 1
                        self.trades[-1]["signal"] = signal.get("reason", "")

            # ── 计算当日权益 ──
            equity = self.cash
            for pc, pp in self.positions.items():
                equity += pp["shares"] * current_price
            daily_equities.append(equity)

        # ── 平仓所有剩余持仓 ──
        if closes:
            final_price = closes[-1]
            for pos_code in list(self.positions.keys()):
                pos = self.positions[pos_code]
                self._close_position(pos_code, final_price, pos["shares"], "回测结束平仓")

        # ── 计算绩效指标 ──
        result.final_equity = self.cash
        result.total_return = round((self.cash - self.initial_capital) / self.initial_capital * 100, 2)
        result.equity_curve = daily_equities

        # 年化收益率
        if raw:
            first_day = raw[min(start_idx, len(raw) - 1)].get("day", "")
            last_day = raw[min(end_idx - 1, len(raw) - 1)].get("day", "")
            try:
                d1 = datetime.strptime(first_day[:10], "%Y-%m-%d")
                d2 = datetime.strptime(last_day[:10], "%Y-%m-%d")
                years = max((d2 - d1).days / 365, 0.02)
                result.annual_return = round(((1 + result.total_return / 100) ** (1 / years) - 1) * 100, 2)
            except Exception as e:
                L.debug(f"年化收益率计算失败: {e}")
                result.annual_return = result.total_return

        # 最大回撤
        if daily_equities:
            peak = daily_equities[0]
            max_dd = 0
            for eq in daily_equities:
                peak = max(peak, eq)
                dd = (peak - eq) / peak * 100 if peak > 0 else 0
                max_dd = max(max_dd, dd)
            result.max_drawdown = round(max_dd, 2)

        # 交易统计
        result.total_trades = len(self.trades)
        winning = [t for t in self.trades if t.get("pnl", 0) > 0]
        losing = [t for t in self.trades if t.get("pnl", 0) < 0]
        result.win_trades = len(winning)
        result.loss_trades = len(losing)
        result.win_rate = round(result.win_trades / max(result.total_trades, 1) * 100, 1)
        result.avg_win = round(sum(t.get("pnl", 0) for t in winning) / max(len(winning), 1), 2)
        result.avg_loss = round(abs(sum(t.get("pnl", 0) for t in losing)) / max(len(losing), 1), 2)

        # 盈利因子
        total_gain = sum(t.get("pnl", 0) for t in winning)
        total_loss = abs(sum(t.get("pnl", 0) for t in losing))
        result.profit_factor = round(total_gain / max(total_loss, 1), 2)

        # 夏普比率
        if len(daily_equities) > 2:
            returns = []
            for j in range(1, len(daily_equities)):
                r = (daily_equities[j] - daily_equities[j - 1]) / max(daily_equities[j - 1], 1)
                returns.append(r)
            if returns:
                import math
                avg_ret = sum(returns) / len(returns)
                variance = sum((r - avg_ret) ** 2 for r in returns) / max(len(returns) - 1, 1)
                std_dev = math.sqrt(variance)
                risk_free = 0.02 / 252
                result.sharpe_ratio = round((avg_ret - risk_free) / max(std_dev, 0.0001) * math.sqrt(252), 2)

        # 月度收益
        monthly = {}
        for t in self.trades:
            try:
                month = t["time"][:7]
                monthly[month] = monthly.get(month, 0) + t.get("pnl", 0)
            except Exception as e:
                L.debug(f"月度收益聚合跳过: {e}")
        result.monthly_returns = {k: round(v, 2) for k, v in sorted(monthly.items())}

        result.trade_log = self.trades
        return result

    def _open_position(self, code, price, shares):
        """开仓 — 100股整数倍，含佣金+过户费"""
        shares = a_share.normalize_lot(shares)
        if shares <= 0:
            return
        cost = shares * price
        commission = max(cost * self._commission_rate, self._min_commission)
        transfer_fee = cost * self._transfer_fee_rate if code.lower().startswith("sh") else 0.0
        total_cost = cost + commission + transfer_fee

        if total_cost > self.cash:
            shares = a_share.normalize_lot((self.cash - self._min_commission) / (price * (1 + self._commission_rate + self._transfer_fee_rate)))
            if shares < 100:
                return
            cost = shares * price
            commission = max(cost * self._commission_rate, self._min_commission)
            transfer_fee = cost * self._transfer_fee_rate if code.lower().startswith("sh") else 0.0
            total_cost = cost + commission + transfer_fee

        self.cash -= total_cost
        self.positions[code] = {"shares": shares, "avg_cost": price}

        self.trades.append({
            "time": datetime.now().strftime("%Y-%m-%d"),
            "action": "buy", "code": code, "price": price,
            "shares": shares, "cost": round(total_cost, 2),
            "commission": round(commission + transfer_fee, 2), "pnl": 0
        })

    def _close_position(self, code, price, shares, reason=""):
        """平仓 — 100股整数倍，含佣金+印花税+过户费"""
        if code not in self.positions:
            return
        pos = self.positions[code]
        actual_shares = a_share.normalize_lot(min(shares, pos["shares"]))
        if actual_shares <= 0:
            return

        revenue = actual_shares * price
        commission = max(revenue * self._commission_rate, self._min_commission)
        stamp_tax = revenue * self._stamp_tax_rate
        transfer_fee = revenue * self._transfer_fee_rate if code.lower().startswith("sh") else 0.0
        net_revenue = revenue - commission - stamp_tax - transfer_fee
        cost_basis = pos["avg_cost"] * actual_shares
        pnl = net_revenue - cost_basis

        self.cash += net_revenue
        pos["shares"] -= actual_shares
        if pos["shares"] <= 0:
            del self.positions[code]

        self.trades.append({
            "time": datetime.now().strftime("%Y-%m-%d"),
            "action": "sell", "code": code, "price": price,
            "shares": actual_shares, "cost": round(net_revenue, 2),
            "commission": round(commission + stamp_tax + transfer_fee, 2),
            "pnl": round(pnl, 2), "reason": reason
        })

    def run_with_gbt_strategies(self, code, kline_data, start_date=None, end_date=None, **params):
        """使用GBT内置的4策略并行回测"""
        try:
            from gbt.strategies import StrategyEngine
            engine = StrategyEngine()

            def gbt_strategy(closes, highs, lows, volumes, idx):
                return engine.analyze(closes, highs, lows, volumes)

            return self.run(code, kline_data, gbt_strategy, start_date, end_date, **params)
        except ImportError:
            L.error("策略引擎未加载")
            return None

    def run_parameter_scan(self, code, kline_data, param_grid, strategy_fn=None, start_date=None, end_date=None):
        """参数网格搜索 — 找出最优参数组合"""
        results = []
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        def _recurse(idx, current_params):
            if idx == len(keys):
                result = self.run(code, kline_data, strategy_fn, start_date, end_date, **current_params)
                results.append((current_params.copy(), result))
                return
            for val in values[idx]:
                current_params[keys[idx]] = val
                _recurse(idx + 1, current_params)

        _recurse(0, {})
        results.sort(key=lambda x: x[1].sharpe_ratio, reverse=True)
        return {
            "best_params": results[0][0] if results else {},
            "best_result": results[0][1].to_dict() if results else {},
            "top5": [
                {"params": p, "sharpe": r.sharpe_ratio, "return": r.total_return, "max_dd": r.max_drawdown}
                for p, r in results[:5]
            ],
            "total_combinations": len(results)
        }

    def summary(self, result):
        """输出回测摘要"""
        return result.summary()


# ── 全局回测引擎 ──
try:
    from gbt.database import db as _db
    backtester = BacktestEngine(db=_db)
except ImportError:
    backtester = BacktestEngine()