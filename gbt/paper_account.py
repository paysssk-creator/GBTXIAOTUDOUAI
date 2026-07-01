"""Paper Trading Account - Real market-connected P&L tracking"""
import json, os, time, threading
from datetime import datetime

ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "..", "paper_account.json")
LOCK = threading.Lock()

DEFAULT_ACCOUNT = {
    "cash": 100000.00,
    "equity": 100000.00,
    "pnl": 0.0,
    "pnl_pct": 0.0,
    "positions": {},
    "orders": [],
    "trade_history": [],
    "created": datetime.now().isoformat(),
    "last_prices": {}
}

def load():
    try:
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
                return json.loads(f.read())
    except Exception as e:
        pass
    return dict(DEFAULT_ACCOUNT)

def save(acct):
    try:
        os.makedirs(os.path.dirname(ACCOUNT_FILE), exist_ok=True)
        with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
            json.dump(acct, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        pass

def get_status():
    """Return current account status with real P&L"""
    with LOCK:
        acct = load()
        positions = acct.get("positions", {})
        total_value = acct["cash"]
        # Update position values from last prices
        for code, pos in list(positions.items()):
            if pos.get("shares", 0) > 0:
                price = acct.get("last_prices", {}).get(code, pos.get("avg_price", 0))
                pos["current_price"] = price
                pos["market_value"] = pos["shares"] * price
                pos["unrealized_pnl"] = pos["market_value"] - pos["shares"] * pos["avg_price"]
                total_value += pos["market_value"]
        acct["equity"] = round(total_value, 2)
        acct["pnl"] = round(total_value - 100000.0, 2)
        acct["pnl_pct"] = round(acct["pnl"] / 100000.0 * 100, 2) if 100000.0 > 0 else 0
        save(acct)
        return {
            "cash": acct["cash"],
            "equity": acct["equity"],
            "pnl": acct["pnl"],
            "pnl_pct": acct["pnl_pct"],
            "positions": len(positions),
            "position_list": list(positions.values()),
            "trade_count": len(acct.get("trade_history", []))
        }

def update_price(code, price):
    """Update last known price from market"""
    with LOCK:
        acct = load()
        acct.setdefault("last_prices", {})[code] = price
        save(acct)

def buy(code, shares, price, name=""):
    """Buy shares at price"""
    with LOCK:
        acct = load()
        cost = shares * price * 1.0003  # commission
        if acct["cash"] < cost:
            return {"ok": False, "error": f"Not enough cash: need {cost:.2f}, have {acct['cash']:.2f}"}
        acct["cash"] = round(acct["cash"] - cost, 2)
        pos = acct.setdefault("positions", {}).setdefault(code, {
            "code": code, "name": name, "shares": 0, "avg_price": 0, "market_value": 0, "unrealized_pnl": 0
        })
        old_total = pos["shares"] * pos["avg_price"]
        pos["shares"] += shares
        pos["avg_price"] = round((old_total + shares * price) / pos["shares"], 3)
        pos["market_value"] = pos["shares"] * price
        acct["last_prices"][code] = price
        acct["trade_history"].append({
            "action": "buy", "code": code, "shares": shares, "price": price,
            "time": datetime.now().isoformat(), "cost": round(cost, 2)
        })
        save(acct)
        return {"ok": True, "shares": pos["shares"], "avg_price": pos["avg_price"], "cost": round(cost, 2)}

def sell(code, shares, price):
    """Sell shares at price"""
    with LOCK:
        acct = load()
        pos = acct.get("positions", {}).get(code)
        if not pos or pos["shares"] < shares:
            return {"ok": False, "error": f"Not enough shares: have {pos['shares'] if pos else 0}, need {shares}"}
        revenue = shares * price * 0.9987  # after stamp tax + commission
        acct["cash"] = round(acct["cash"] + revenue, 2)
        pos["shares"] -= shares
        if pos["shares"] <= 0:
            del acct["positions"][code]
        else:
            pos["market_value"] = pos["shares"] * price
        acct["last_prices"][code] = price
        acct["trade_history"].append({
            "action": "sell", "code": code, "shares": shares, "price": price,
            "time": datetime.now().isoformat(), "revenue": round(revenue, 2)
        })
        save(acct)
        return {"ok": True, "shares": pos.get("shares", 0) if code in acct.get("positions", {}) else 0, "revenue": round(revenue, 2)}
