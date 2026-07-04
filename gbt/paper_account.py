"""
Paper Trading Account — 模拟交易账户（可量化、可查询每笔成交）
"""
import json, os, time
from datetime import datetime, timedelta

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "paper_account.json")

def _init_state():
    return {
        "cash": 100000.0,
        "equity": 100000.0,
        "pnl": 0.0,
        "positions": {},   # {code: {shares, avg_cost, market_price, market_value, pnl}}
        "orders": [],       # [{id, time, code, name, side, price, shares, status}]
        "trades": [],       # [{id, time, code, name, side, price, shares, value}]
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

def _load():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    s = _init_state()
    _save(s)
    return s

def _save(state):
    state["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_state():
    """完整账户状态"""
    s = _load()
    # recalculate equity
    equity = s.get("cash", 0)
    total_pnl = 0.0
    for pos in s.get("positions", {}).values():
        equity += pos.get("market_value", 0)
        total_pnl += pos.get("pnl", 0)
    s["equity"] = round(equity, 2)
    s["total_pnl"] = round(total_pnl, 2)
    s["position_count"] = len(s.get("positions", {}))
    return s

def place_order(code, name, side, price, shares):
    """下单 — BUY/SELL"""
    s = _load()
    cost = round(price * shares, 2)
    order_id = f"ORD-{int(time.time()*1000)}"
    
    if side.upper() == "BUY":
        if s.get("cash", 0) < cost:
            return {"ok": False, "error": f"资金不足: 需¥{cost:,.2f}，可用¥{s['cash']:,.2f}"}
        s["cash"] = round(s["cash"] - cost, 2)
        # update position
        if code not in s["positions"]:
            s["positions"][code] = {"code": code, "name": name, "shares": 0, "avg_cost": 0.0,
                                    "market_price": price, "market_value": 0.0, "pnl": 0.0}
        pos = s["positions"][code]
        total_shares = pos["shares"] + shares
        pos["avg_cost"] = round((pos["avg_cost"] * pos["shares"] + cost) / total_shares, 4)
        pos["shares"] = total_shares
        pos["market_price"] = price
        pos["market_value"] = round(total_shares * price, 2)
        pos["pnl"] = round(pos["market_value"] - total_shares * pos["avg_cost"], 2)
    else:  # SELL
        if code not in s["positions"]:
            return {"ok": False, "error": f"无持仓: {code}"}
        pos = s["positions"][code]
        if pos["shares"] < shares:
            return {"ok": False, "error": f"持仓不足: 持有{pos['shares']}股，卖出{shares}股"}
        s["cash"] = round(s["cash"] + cost, 2)
        pos["shares"] -= shares
        pos["market_price"] = price
        pos["market_value"] = round(pos["shares"] * price, 2)
        pos["pnl"] = round(pos["market_value"] - pos["shares"] * pos["avg_cost"], 2)
        if pos["shares"] == 0:
            s["positions"].pop(code, None)
    
    # record trade
    trade = {
        "id": order_id,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "code": code,
        "name": name,
        "side": side.upper(),
        "price": price,
        "shares": shares,
        "value": cost,
    }
    s["trades"].append(trade)
    s["orders"].append({**trade, "status": "FILLED"})
    
    # recalc pnl
    s["pnl"] = round(s["equity"] - 100000.0, 2)
    _save(s)
    return {"ok": True, "order_id": order_id, "trade": trade, "cash": s["cash"],
            "positions": list(s["positions"].values())}

def get_trades(limit=50):
    """成交记录"""
    s = _load()
    return s.get("trades", [])[-limit:]

def get_orders(limit=50):
    """委托记录"""
    s = _load()
    return s["orders"][-limit:]

def reset():
    """重置账户"""
    s = _init_state()
    _save(s)
    return {"ok": True, "cash": s["cash"]}
