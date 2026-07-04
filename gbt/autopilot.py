"""
GBT 自主操盘引擎 — Auto Pilot
核心: 自动扫描 → AI分析 → 决策 → 下单 → 监控 全程无人值守
"""
import json, os, time, threading, logging
from datetime import datetime

L = logging.getLogger("gbt.autopilot")

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "autopilot.json")

WATCHLIST = [("600519", "贵州茅台"), ("600036", "招商银行"), ("000001", "平安银行"),
             ("000858", "五粮液"), ("601318", "中国平安")]

class AutoPilot:
    def __init__(self):
        self.running = False
        self.thread = None
        self.state = self._load()
        self.lock = threading.Lock()
        L.info("AutoPilot initialized")

    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "running": False,
            "mode": "conservative",  # conservative / aggressive
            "max_capital_pct": 30,   # 单只最大仓位%
            "stop_loss_pct": -5.0,   # 止损线%
            "take_profit_pct": 10.0, # 止盈线%
            "scan_interval_sec": 60, # 扫描间隔
            "auto_trade_enabled": True,
            "logs": [],
            "scan_count": 0,
            "trade_count": 0,
            "signal_count": 0,
            "last_scan": None,
            "pnl": 0.0,
        }

    def _save(self):
        with self.lock:
            self.state["running"] = self.running
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)

    def log(self, msg, level="info"):
        entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 200:
            self.state["logs"] = self.state["logs"][-200:]
        L.info(entry)
        self._save()

    def start(self):
        if self.running:
            return {"ok": False, "error": "自主操盘已在运行"}
        self.running = True
        self.log("自主操盘引擎启动")
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self._save()
        return {"ok": True, "message": "自主操盘引擎已启动", "mode": self.state["mode"]}

    def stop(self):
        self.running = False
        self.log("自主操盘引擎停止")
        self._save()
        return {"ok": True, "message": "自主操盘引擎已停止"}

    def status(self):
        with self.lock:
            logs = list(self.state.get("logs", [])[-30:])
            return {
                "running": self.running,
                "mode": self.state["mode"],
                "scan_count": self.state["scan_count"],
                "trade_count": self.state["trade_count"],
                "signal_count": self.state["signal_count"],
                "pnl": self.state.get("pnl", 0),
                "last_scan": self.state.get("last_scan"),
                "auto_trade_enabled": self.state["auto_trade_enabled"],
                "stop_loss_pct": self.state["stop_loss_pct"],
                "take_profit_pct": self.state["take_profit_pct"],
                "watchlist": WATCHLIST,
                "logs": logs,
            }

    def update_config(self, cfg):
        for k in ("mode", "max_capital_pct", "stop_loss_pct", "take_profit_pct",
                  "scan_interval_sec", "auto_trade_enabled"):
            if k in cfg:
                self.state[k] = cfg[k]
        self._save()
        self.log(f"配置更新: {cfg}")
        return {"ok": True, "config": self.state}

    # ── 核心循环 ──
    def _loop(self):
        self.log("自主循环开始 — 扫描间隔 %ds" % self.state["scan_interval_sec"])
        while self.running:
            try:
                self._scan_and_decide()
            except Exception as e:
                self.log(f"循环异常: {e}", "error")
            time.sleep(self.state["scan_interval_sec"])

    def _scan_and_decide(self):
        """一次扫描 + AI决策 + 自动交易"""
        self.state["scan_count"] += 1
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        self.state["last_scan"] = t
        self.log(f"第{self.state['scan_count']}次扫描 — {t}")

        # 1. 获取行情（优先真实数据）
        from gbt.paper_account import get_state as _pa
        account = _pa()
        cash = account.get("cash", 100000)
        positions = account.get("positions", {})

        # 尝试真实行情
        quotes_map = {}
        klines_map = {}
        try:
            from gbt.live_market import get_market
            market = get_market()
            for code, name in WATCHLIST:
                q = market.get_quote(code)
                if q:
                    quotes_map[code] = q
                k = market.get_daily_kline(code, 30)
                if k:
                    klines_map[code] = k
            if quotes_map:
                self.log(f"真实行情获取: {len(quotes_map)}只")
        except Exception as e:
            self.log(f"行情获取回退模拟: {e}", "warning")

        # 2. AI决策引擎 — DeepSeek-reasoner 深度推理
        from gbt.ai_decision import get_engine
        engine = None
        try:
            import os as _os
            if _os.environ.get("DEEPSEEK_API_KEY"):
                from gbt.llm import GBTLLM
                reasoner_model = _os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner")
                llm = GBTLLM(provider="deepseek", model=reasoner_model)
                engine = get_engine(llm=llm)
                self.log(f"DeepSeek推理引擎: {llm.model}")
        except Exception as e:
            self.log(f"推理引擎回退: {e}", "warning")
        if engine is None:
            engine = get_engine()

        from gbt.notifier import get_notifier
        notify = get_notifier()
        from gbt.audit import get_audit
        audit = get_audit()

        signals = []
        for code, name in WATCHLIST:
            q = quotes_map.get(code)
            if not q:
                import hashlib
                seed = int(hashlib.md5(f"{code}{self.state['scan_count']}".encode()).hexdigest()[:4], 16)
                base_price = {"600519": 1650, "600036": 38.5, "000001": 12.3, "000858": 142, "601318": 45}[code]
                q = {
                    "code": code, "name": name,
                    "price": round(base_price * (1 + (seed % 200 - 100) / 10000), 2),
                    "change_pct": round((seed % 200 - 100) / 100, 2),
                }

            kl = klines_map.get(code)
            decision = engine.analyze(quote=q, klines=kl, positions=positions,
                                      account=account, mode=self.state["mode"])
            audit.signal(code, decision.signal, decision.confidence, decision.reasoning)

            signals.append({
                "code": code, "name": name,
                "price": decision.price, "change_pct": decision.change_pct,
                "scanned_at": t, "signal": decision.signal,
                "reason": decision.reasoning,
                "confidence": decision.confidence,
                "indicators": decision.indicators,
                "position_shares": getattr(decision, "position_shares", 0),
                "position_size": decision.position_size,
            })

        self.state["signals"] = signals
        self.state["signal_count"] += 1

        # 3. 执行交易
        if self.state["auto_trade_enabled"] and self.running:
            from gbt.paper_account import place_order
            for sig in signals:
                if sig["signal"] == "BUY" and cash > 5000:
                    max_spend = cash * self.state["max_capital_pct"] / 100
                    shares = min(int(max_spend / sig["price"] / 100) * 100, 500)
                    if shares >= 100:
                        result = place_order(sig["code"], sig["name"], "BUY", sig["price"], shares)
                        if result.get("ok"):
                            self.state["trade_count"] += 1
                            oid = result.get("order_id", "")
                            self.log(f"买入 {sig['name']}({sig['code']}) {shares}股 @¥{sig['price']} — {sig['reason']}")
                            audit.trade("BUY", sig["code"], sig["name"], sig["price"], shares, oid)
                            notify.trade_alert("BUY", sig["code"], sig["name"], sig["price"], shares, sig["reason"])
                        else:
                            self.log(f"买入失败: {result.get('error')}", "error")
                elif sig["signal"] == "SELL" and sig.get("position_shares", 0) > 0:
                    shares = sig["position_shares"]
                    result = place_order(sig["code"], sig["name"], "SELL", sig["price"], shares)
                    if result.get("ok"):
                        self.state["trade_count"] += 1
                        oid = result.get("order_id", "")
                        self.log(f"卖出 {sig['name']}({sig['code']}) {shares}股 @¥{sig['price']} — {sig['reason']}")
                        audit.trade("SELL", sig["code"], sig["name"], sig["price"], shares, oid)
                        notify.trade_alert("SELL", sig["code"], sig["name"], sig["price"], shares, sig["reason"])
                        if "止损" in sig.get("reason", ""):
                            notify.stop_alert(sig["code"], sig["name"], sig.get("pnl_pct", 0), sig["price"])
                    else:
                        self.log(f"卖出失败: {result.get('error')}", "error")
        # 3. 更新盈亏
        from gbt.paper_account import get_state
        new_state = get_state()
        self.state["pnl"] = new_state.get("total_pnl", 0)
        self._save()


# 全局单例
_pilot = None

def get_pilot():
    global _pilot
    if _pilot is None:
        _pilot = AutoPilot()
    return _pilot
