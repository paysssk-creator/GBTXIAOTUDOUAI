"""
brain.py — GBT 自主AI大脑 v2
持续感知环境 → 自主决策 → 连贯调用所有能力
不等待用户指令，主动判断"什么时候该做什么事"
"""
import os, sys, time, threading, json, logging, re
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Brain")

# ── 大脑决策 ──
class AutonomousBrain:
    """主动AI大脑 — 持续运行，自主决策"""
    
    def __init__(self, trader=None, watcher=None, llm=None, account=None, desktop_ctl=None):
        self.trader = trader
        self.watcher = watcher
        self.llm = llm
        self.account = account
        self.desktop_ctl = desktop_ctl
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # 决策历史
        self.decisions = deque(maxlen=200)
        self.current_plan = None
        
        # 上下文记忆 (让AI连贯思考)
        self.context = deque(maxlen=20)
        self.last_check = {}
        
        # 能力注册表 — AI 知道自己有哪些能力
        self.capabilities = [
            "market_scan",      # 全市场扫描
            "stock_analyze",    # 单股深度分析
            "tech_analysis",    # 技术指标
            "strategy_eval",    # 策略评估
            "trade_execute",    # 执行交易
            "desktop_control",  # 电脑操控
            "send_notification",# 桌面通知
            "web_search",       # 网络搜索
            "system_monitor",   # 系统监控
            "connection_health",# 连接健康检查
            "log_analysis",     # 日志分析
            "file_operation",   # 文件操作
        ]
    
    def start(self):
        if self.thread and self.thread.is_alive():
            return {"ok": False, "msg": "大脑已在运行"}
        self.running = True
        self.thread = threading.Thread(target=self._brain_loop, daemon=True)
        self.thread.start()
        L.info("🧠 自主AI大脑已启动 — 持续感知 + 自主决策 + 能力连贯调用")
        return {"ok": True, "msg": "大脑已启动"}
    
    def stop(self):
        self.running = False
        return {"ok": True, "msg": "大脑已停止"}
    
    def _brain_loop(self):
        """大脑主循环 — 持续感知→思考→行动"""
        L.info("🧠 大脑循环启动")
        time.sleep(3)  # 等子系统初始化
        
        while self.running:
            try:
                now = datetime.now()
                hour = now.hour + now.minute / 60.0
                is_trading = (9.5 <= hour <= 11.5) or (13.0 <= hour <= 15.0)
                
                # ═══ 阶段1: 感知 (Sense) ═══
                perception = self._sense(now, is_trading)
                
                # ═══ 阶段2: 思考 (Think) ═══
                action = self._think(perception, now, is_trading)
                
                # ═══ 阶段3: 行动 (Act) ═══
                if action:
                    self._act(action, now)
                
                # 自适应休眠
                if is_trading:
                    time.sleep(30)   # 交易时段高频
                elif action and action.get("priority") == "critical":
                    time.sleep(10)   # 紧急事件快速响应
                else:
                    time.sleep(60)   # 非交易时段节能
                    
            except Exception as e:
                L.error(f"大脑循环异常: {e}")
                time.sleep(30)
    
    def _sense(self, now, is_trading):
        """感知环境状态 — 收集所有信息源"""
        perception = {
            "time": now.strftime("%H:%M:%S"),
            "is_trading": is_trading,
            "alerts": [],
            "connections": {},
            "market_snapshot": {},
            "account_status": {},
            "system_health": {}
        }
        
        # 1. 守夜人告警
        if self.watcher:
            try:
                ws = self.watcher.get_status()
                perception["system_health"] = ws
                # 提取活跃告警
                for name, status in ws.get("monitors", {}).items():
                    if status.get("status") == "critical":
                        perception["alerts"].append({
                            "source": "watcher",
                            "monitor": name,
                            "level": "critical",
                            "detail": status.get("details", "")
                        })
            except: pass
        
        # 2. 连接状态
        try:
            from gbt.mcp import get_mcp
            mcp = get_mcp()
            for name, srv in mcp._servers.items():
                perception["connections"][name] = srv.status.value if hasattr(srv, 'status') else "unknown"
        except: pass
        
        # 3. 市场快照 (交易时段)
        if is_trading and self.trader:
            try:
                data = self.trader.fetch_watchlist()
                up = sum(1 for q in data.values() if q.change_pct > 0)
                down = sum(1 for q in data.values() if q.change_pct < 0)
                perception["market_snapshot"] = {
                    "total": len(data),
                    "up": up, "down": down,
                    "bias": round((up - down) / max(len(data), 1) * 100, 1)
                }
            except: pass
        
        # 4. 账户状态
        if self.account:
            try:
                perception["account_status"] = {
                    "cash": self.account.cash,
                    "positions": len(self.account.positions),
                    "total_pnl": self.account.total_pnl,
                    "daily_pnl": self.account.daily_pnl
                }
            except: pass
        
        return perception
    
    def _think(self, perception, now, is_trading):
        """AI思考 — 分析感知数据，决定下一步行动"""
        action = None
        priority = "normal"
        
        # ── 规则1: 紧急告警 → 立即通知 ──
        for alert in perception.get("alerts", []):
            if alert.get("level") == "critical":
                action = {
                    "type": "alert_response",
                    "priority": "critical",
                    "reason": f"守夜人检测到: {alert.get('monitor')}",
                    "chain": ["send_notification", "auto_fix"]
                }
                priority = "critical"
                break
        
        # ── 规则2: 连接失效 → 自动修复 ──
        if not action:
            for name, status in perception.get("connections", {}).items():
                if status in ("offline", "error", "timeout"):
                    action = {
                        "type": "connection_recovery",
                        "priority": "high",
                        "reason": f"连接断开: {name} ({status})",
                        "chain": ["connection_health", "auto_fix", "log_analysis"],
                        "target": name
                    }
                    break
        
        # ── 规则3: 交易时段市场异动 → 深度分析 ──
        if not action and is_trading and perception.get("market_snapshot", {}).get("bias", 0) != 0:
            bias = perception["market_snapshot"]["bias"]
            if abs(bias) > 60:  # 极端分化
                action = {
                    "type": "market_anomaly",
                    "priority": "high",
                    "reason": f"市场极端分化: {'普涨' if bias > 0 else '普跌'} {abs(bias)}%",
                    "chain": ["market_scan", "stock_analyze", "strategy_eval", "send_notification"]
                }
            elif abs(bias) > 40:  # 明显分化
                action = {
                    "type": "market_alert",
                    "priority": "medium",
                    "reason": f"市场明显偏向: {'多方' if bias > 0 else '空方'} {abs(bias)}%",
                    "chain": ["stock_analyze", "strategy_eval"]
                }
        
        # ── 规则4: 账户大额盈亏 → 风控检查 ──
        if not action and self.account:
            try:
                daily = self.account.daily_pnl
                if abs(daily) > 5000:
                    action = {
                        "type": "risk_alert",
                        "priority": "high",
                        "reason": f"日盈亏 ¥{daily:.0f} 触发风控审查",
                        "chain": ["strategy_eval", "trade_execute" if daily < -3000 else "send_notification"]
                    }
            except: pass
        
        # ── 规则5: 定期健康检查 (每10分钟) ──
        if not action:
            last = self.last_check.get("system_health", 0)
            if time.time() - last > 600:
                action = {
                    "type": "health_check",
                    "priority": "low",
                    "reason": "定时系统健康巡检",
                    "chain": ["system_monitor", "connection_health"]
                }
        
        if action:
            action["priority"] = priority
            action["time"] = now.strftime("%H:%M:%S")
            with self._lock:
                self.decisions.appendleft(action)
            L.info(f"🧠 决策: [{priority}] {action['type']} → {' → '.join(action['chain'])}")
        
        return action
    
    def _act(self, action, now):
        """执行行动链 — 连贯调用多个能力"""
        chain = action.get("chain", [])
        results = []
        
        for step in chain:
            try:
                if step == "send_notification" and self.trader:
                    r = self.trader.send_notification(
                        f"GBT大脑",
                        f"{action.get('reason','')}"
                    )
                    results.append({"step": step, "ok": r.get("ok", False)})
                
                elif step == "market_scan" and self.trader:
                    L.info("🧠 大脑触发: 全市场扫描")
                    # 不阻塞 — 由交易循环处理
                    results.append({"step": step, "ok": True, "delegated": True})
                
                elif step == "stock_analyze" and self.trader:
                    # 对持仓股做深度分析
                    if self.account and self.account.positions:
                        for code in list(self.account.positions.keys())[:3]:
                            try:
                                q = self.trader.fetch_quote([code])
                                if code in q:
                                    sig = self.trader.analyze_with_ai(code, q[code])
                                    results.append({"step": step, "code": code, 
                                                  "action": sig.action, "confidence": sig.confidence})
                            except: pass
                
                elif step == "system_monitor" and self.watcher:
                    ws = self.watcher.get_status()
                    issues = sum(1 for m in ws.get("monitors",{}).values() 
                               if m.get("status") in ("warn","critical"))
                    results.append({"step": step, "ok": True, "issues": issues})
                    self.last_check["system_health"] = time.time()
                
                elif step == "connection_health":
                    try:
                        from gbt.mcp import get_mcp, call_mcp
                        mcp = get_mcp()
                        down = []
                        for name, srv in mcp._servers.items():
                            try:
                                r = call_mcp(name, "status", timeout=5)
                                if not r.ok:
                                    down.append(name)
                            except:
                                down.append(name)
                        if down:
                            L.warning(f"🧠 连接异常: {', '.join(down)}")
                        results.append({"step": step, "ok": True, "total": len(mcp._servers), "down": len(down)})
                    except Exception as e:
                        results.append({"step": step, "ok": False, "error": str(e)})
                
                elif step == "auto_fix" and self.watcher:
                    L.info("🧠 大脑触发: 自动修复扫描")
                    results.append({"step": step, "ok": True, "delegated": True})
                
                elif step == "strategy_eval":
                    L.info("🧠 大脑触发: 策略重评估")
                    results.append({"step": step, "ok": True, "delegated": True})
                
                elif step == "log_analysis":
                    L.info("🧠 大脑: 日志检查")
                    results.append({"step": step, "ok": True, "scanned": True})
                
            except Exception as e:
                L.error(f"🧠 执行失败 [{step}]: {e}")
                results.append({"step": step, "ok": False, "error": str(e)})
        
        with self._lock:
            self.context.appendleft({
                "time": now.strftime("%H:%M:%S"),
                "action": action["type"],
                "priority": action.get("priority", "normal"),
                "results": results
            })
    
    def get_status(self):
        """获取大脑运行状态"""
        return {
            "running": self.running,
            "decisions": list(self.decisions)[:20],
            "context": list(self.context)[:10],
            "last_checks": self.last_check,
            "capabilities": self.capabilities
        }


# ── 全局单例 ──
brain = AutonomousBrain()
