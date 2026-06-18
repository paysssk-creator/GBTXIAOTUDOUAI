"""
账户追踪器 — 现金/持仓/盈亏
"""
import logging
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Account")


class Account:
    """交易账户"""

    def __init__(self, initial_cash=100000, db=None):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}       # {code: {shares, avg_cost, name}}
        self.trade_log = deque(maxlen=200)
        self.daily_pnl = 0
        self.total_pnl = 0
        self.total_trades = 0
        self.win_trades = 0
        self.loss_trades = 0
        self.created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db = db  # SQLite database reference

    def get_equity(self, market_prices=None):
        """
        总资产 = 现金 + 持仓市值
        market_prices: {code: current_price}
        """
        total = self.cash
        for code, pos in self.positions.items():
            price = market_prices.get(code, pos["avg_cost"]) if market_prices else pos["avg_cost"]
            total += pos["shares"] * price
        return round(total, 2)

    def get_position_value(self, code, current_price=None):
        """单票市值"""
        if code not in self.positions:
            return 0
        pos = self.positions[code]
        price = current_price or pos["avg_cost"]
        return round(pos["shares"] * price, 2)

    def get_pnl(self, market_prices=None):
        """
        总盈亏
        """
        equity = self.get_equity(market_prices)
        return {
            "equity": equity,
            "cash": round(self.cash, 2),
            "pnl": round(equity - self.initial_cash, 2),
            "pnl_pct": round((equity - self.initial_cash) / self.initial_cash * 100, 2),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_trades / max(self.total_trades, 1) * 100, 1),
            "daily_pnl": round(self.daily_pnl, 2)
        }

    def buy(self, code, name, shares, price):
        """买入"""
        cost = shares * price
        if cost > self.cash:
            return {"ok": False, "error": f"资金不足 (需{cost:.0f} 余额{self.cash:.0f})"}

        self.cash -= cost

        if code in self.positions:
            pos = self.positions[code]
            total_shares = pos["shares"] + shares
            total_cost = pos["avg_cost"] * pos["shares"] + cost
            pos["shares"] = total_shares
            pos["avg_cost"] = round(total_cost / total_shares, 2)
        else:
            self.positions[code] = {"shares": shares, "avg_cost": price, "name": name}

        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "buy",
            "code": code,
            "name": name,
            "shares": shares,
            "price": price,
            "amount": round(cost, 2),
            "cash_after": round(self.cash, 2)
        }
        self.trade_log.appendleft(entry)
        self.total_trades += 1

        # ── SQLite 持久化 ──
        if self.db:
            try:
                self.db.add_trade(
                    time=entry["time"], action="buy", code=code, name=name,
                    shares=shares, price=price, amount=round(cost, 2),
                    cash_after=round(self.cash, 2)
                )
                self.db.upsert_position(code, name, self.positions[code]["shares"], self.positions[code]["avg_cost"])
                self.db.update_account(cash=self.cash, total_trades=self.total_trades, win_trades=self.win_trades, loss_trades=self.loss_trades)
            except Exception as e:
                L.warning(f"DB写入失败: {e}")

        L.info(f"💰 买入 {name}({code}) {shares}股 @ {price:.2f} = ¥{cost:.0f}")
        return {"ok": True, "entry": entry}

    def sell(self, code, shares, price):
        """卖出"""
        if code not in self.positions:
            return {"ok": False, "error": f"无持仓: {code}"}

        pos = self.positions[code]
        if shares > pos["shares"]:
            shares = pos["shares"]

        revenue = shares * price
        cost_basis = pos["avg_cost"] * shares
        pnl = revenue - cost_basis

        self.cash += revenue
        self.total_pnl += pnl
        self.daily_pnl += pnl

        if pnl > 0:
            self.win_trades += 1
        elif pnl < 0:
            self.loss_trades += 1

        pos["shares"] -= shares
        if pos["shares"] <= 0:
            del self.positions[code]
        else:
            pos["avg_cost"] = round((pos["avg_cost"] * (pos["shares"] + shares) - cost_basis) / max(pos["shares"], 1), 2)

        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "sell",
            "code": code,
            "name": pos.get("name", code),
            "shares": shares,
            "price": price,
            "amount": round(revenue, 2),
            "pnl": round(pnl, 2),
            "cash_after": round(self.cash, 2)
        }
        self.trade_log.appendleft(entry)
        self.total_trades += 1

        # ── SQLite 持久化 ──
        if self.db:
            try:
                self.db.add_trade(
                    time=entry["time"], action="sell", code=code, name=pos.get("name", code),
                    shares=shares, price=price, amount=round(revenue, 2),
                    pnl=round(pnl, 2), cash_after=round(self.cash, 2)
                )
                if code in self.positions:
                    self.db.upsert_position(code, pos.get("name", code), self.positions[code]["shares"], self.positions[code]["avg_cost"])
                else:
                    self.db.delete_position(code)
                self.db.update_account(cash=self.cash, total_pnl=self.total_pnl, daily_pnl=self.daily_pnl,
                                       total_trades=self.total_trades, win_trades=self.win_trades, loss_trades=self.loss_trades)
            except Exception as e:
                L.warning(f"DB写入失败: {e}")

        L.info(f"💰 卖出 {entry['name']}({code}) {shares}股 @ {price:.2f} = ¥{revenue:.0f} | PnL: ¥{pnl:.0f}")
        return {"ok": True, "entry": entry}

    def get_positions_with_value(self, market_prices=None):
        """持仓含市值"""
        result = {}
        for code, pos in self.positions.items():
            price = market_prices.get(code, pos["avg_cost"]) if market_prices else pos["avg_cost"]
            value = pos["shares"] * price
            pnl = (price - pos["avg_cost"]) * pos["shares"]
            pnl_pct = round((price - pos["avg_cost"]) / pos["avg_cost"] * 100, 2) if pos["avg_cost"] else 0
            result[code] = {
                **pos,
                "current_price": price,
                "value": round(value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": pnl_pct
            }
        return result

    def reset_daily(self):
        self.daily_pnl = 0

    def get_config(self):
        return {
            "initial_cash": self.initial_cash,
            "cash": round(self.cash, 2),
            "equity": self.get_equity(),
            "positions_count": len(self.positions),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_trades / max(self.total_trades, 1) * 100, 1),
            "created": self.created
        }


# 全局账户
try:
    from gbt.database import db as _db
    account = Account(initial_cash=100000, db=_db)
    # 从DB恢复账户状态
    acct_data = _db.get_account()
    if acct_data:
        account.cash = acct_data["cash"]
        account.total_pnl = acct_data["total_pnl"]
        account.daily_pnl = acct_data["daily_pnl"]
        account.total_trades = acct_data["total_trades"]
        account.win_trades = acct_data["win_trades"]
        account.loss_trades = acct_data["loss_trades"]
    # 恢复持仓
    for pos in _db.get_positions():
        account.positions[pos["code"]] = {
            "shares": pos["shares"], "avg_cost": pos["avg_cost"], "name": pos["name"]
        }
except ImportError:
    account = Account(initial_cash=100000)
