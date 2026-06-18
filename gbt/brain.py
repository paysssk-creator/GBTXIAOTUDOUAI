"""
brain.py — GBT 自主AI大脑 v3
事件驱动心跳 + 外部触发唤醒 + 自适应感知
不等待用户指令，不靠sleep死等，真正主动干活
"""
import os, sys, time, threading, json, logging, re
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Brain")

class AutonomousBrain:
    """主动AI大脑 — 事件驱动，自主决策"""
    
    def __init__(self, trader=None, watcher=None, llm=None, account=None, desktop_ctl=None):
        self.trader = trader
        self.watcher = watcher
        self.llm = llm
        self.account = account
        self.desktop_ctl = desktop_ctl
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # 事件驱动心跳
        self._heartbeat_event = threading.Event()
        self._beat_count = 0
        self._last_beat = time.time()
        self._beat_interval = 5  # 基础心跳间隔(秒)
        
        # 决策历史
        self.decisions = deque(maxlen=200)
        self.context = deque(maxlen=20)
        self.last_check = {}
        
        # 触发器计数器
        self.triggers = {}
        
        # 能力注册表
        self.capabilities = [
            "market_scan", "stock_analyze", "tech_analysis",
            "strategy_eval", "trade_execute", "desktop_control",
            "send_notification", "web_search", "system_monitor",
            "connection_health", "log_analysis", "file_operation",
        ]
        # 能力 → 依赖前提
        self.cap_prerequisites = {
            "market_scan": ["connection_health"],
            "stock_analyze": ["market_scan"],
            "trade_execute": ["stock_analyze", "strategy_eval"],
        }
    
    def start(self):
        if self.thread and self.thread.is_alive():
            return {"ok": False, "msg": "大脑已在运行"}
        self.running = True
        self._heartbeat_event.clear()
        self.thread = threading.Thread(target=self._brain_loop, daemon=True)
        self.thread.start()
        L.info("🧠 自主AI大脑已启动 — 事件驱动心跳 + 外部触发唤醒")
        return {"ok": True, "msg": "大脑已启动"}
    
    def stop(self):
        self.running = False
        self._heartbeat_event.set()  # 唤醒以退出
        return {"ok": True, "msg": "大脑已停止"}
    
    def ping(self, source="external", reason=""):
        """外部触发唤醒 — 守夜人/交易引擎发现问题时立即唤醒大脑"""
        self._heartbeat_event.set()
        with self._lock:
            self.triggers[source] = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "reason": reason,
                "count": self.triggers.get(source, {}).get("count", 0) + 1
            }
        L.debug(f"⚡ 大脑被唤醒: {source} — {reason}")
    
    def _brain_loop(self):
        """大脑主循环 — 事件驱动 + 自适应心跳"""
        L.info("🧠 大脑循环启动 — 等待外围系统就绪...")
        time.sleep(3)
        
        while self.running:
            try:
                now = datetime.now()
                hour = now.hour + now.minute / 60.0
                is_trading = (9.5 <= hour <= 11.5) or (13.0 <= hour <= 15.0)
                triggered = self._heartbeat_event.is_set()
                
                # 心跳日志(每30秒)
                self._beat_count += 1
                if self._beat_count % 6 == 0:
                    elapsed = time.time() - self._last_beat
                    L.debug(f"💓 心跳 #{self._beat_count} (间隔{elapsed:.1f}s) {'⚡被唤醒' if triggered else '定时'}")
                    self._last_beat = time.time()
                
                # ═══ 阶段1: 感知 ═══
                perception = self._sense(now, is_trading, triggered)
                
                # ═══ 阶段2: 思考 → 决策 ═══
                action = self._think(perception, now, is_trading, triggered)
                
                # ═══ 阶段3: 行动 ═══
                if action:
                    self._act(action, now)
                
                # 自适应心跳间隔
                if triggered:
                    # 被外部唤醒 → 快速响应后短暂休眠
                    self._heartbeat_event.clear()
                    wait_time = max(2, self._beat_interval // 3)
                elif is_trading:
                    wait_time = self._beat_interval  # 交易时段快速循环
                elif action and action.get("priority") == "critical":
                    wait_time = 3  # 紧急事件快速跟进
                else:
                    wait_time = max(10, self._beat_interval * 3)  # 非交易时段节能
                
                # 等待下一次心跳或外部唤醒
                self._heartbeat_event.wait(timeout=wait_time)
                
            except Exception as e:
                L.error(f"大脑循环异常: {e}")
                self._heartbeat_event.wait(timeout=10)
    
    def _sense(self, now, is_trading, triggered):
        """感知环境"""
        p = {
            "time": now.strftime("%H:%M:%S"),
            "is_trading": is_trading,
            "triggered": triggered,
            "alerts": [],
            "connections": {},
            "market_snapshot": {},
            "account_status": {},
        }
        
        # 1. 守夜人告警
        if self.watcher:
            try:
                ws = self.watcher.get_status()
                for name, st in ws.get("monitors", {}).items():
                    if st.get("status") in ("critical", "error"):
                        p["alerts"].append({
                            "source": name, "level": "critical",
                            "detail": st.get("details", ""),
                            "last": st.get("last_check", "")
                        })
            except: pass
        
        # 2. MCP连接
        try:
            from gbt.mcp import get_mcp
            mcp = get_mcp()
            down_count = 0
            for name, srv in mcp._s.items():
                online = getattr(srv, 'status', None)
                if online and hasattr(online, 'value'):
                    online = online.value
                p["connections"][name] = online or "unknown"
                if online not in ("online", "connected"):
                    down_count += 1
            p["connections_down"] = down_count
        except: pass
        
        # 3. 市场快照
        if is_trading and self.trader:
            try:
                data = self.trader.fetch_watchlist()
                up = sum(1 for q in data.values() if getattr(q, 'change_pct', 0) > 0)
                down = sum(1 for q in data.values() if getattr(q, 'change_pct', 0) < 0)
                p["market_snapshot"] = {
                    "total": len(data),
                    "up": up, "down": down,
                    "bias": round((up-down)/max(len(data),1)*100, 1)
                }
            except: pass
        
        # 4. 账户
        if self.account:
            try:
                p["account_status"] = {
                    "cash": self.account.cash,
                    "positions": len(self.account.positions),
                    "daily_pnl": self.account.daily_pnl,
                    "total_pnl": self.account.total_pnl
                }
            except: pass
        
        return p
    
    def _think(self, p, now, is_trading, triggered):
        """决策引擎 — 五层规则 """
        
        # 规则1: 被外部唤醒 → 立即检查告警源
        if triggered and p.get("alerts"):
            alert = p["alerts"][0]
            return {
                "type": "alert_response",
                "priority": "critical",
                "reason": f"⚡ 外部唤醒: {alert['source']} — {alert.get('detail','')}",
                "chain": ["connection_health", "system_monitor", "send_notification"],
                "triggered_by": alert["source"]
            }
        
        # 规则2: MCP连接断连（冷却60秒防止死循环）
        if p.get("connections_down", 0) > 0:
            last_conn_fix = self.last_check.get("connections", 0)
            if time.time() - last_conn_fix > 60:
                self.last_check["connections"] = time.time()
                return {
                    "type": "connection_recovery",
                    "priority": "high",
                    "reason": f"🔌 {p['connections_down']}个MCP服务断连",
                    "chain": ["connection_health", "log_analysis", "send_notification"],
                }
        
        # 规则3: 交易时段市场异动
        if is_trading:
            bias = p.get("market_snapshot", {}).get("bias", 0)
            if abs(bias) > 60:
                return {
                    "type": "market_anomaly",
                    "priority": "high",
                    "reason": f"市场极端: {'普涨' if bias>0 else '普跌'} {abs(bias)}%",
                    "chain": ["market_scan", "stock_analyze", "strategy_eval", "send_notification"],
                }
            elif abs(bias) > 40:
                return {
                    "type": "market_alert",
                    "priority": "medium",
                    "reason": f"市场偏向: {'多方' if bias>0 else '空方'} {abs(bias)}%",
                    "chain": ["stock_analyze", "strategy_eval"],
                }
        
        # 规则4: 账户风控
        if self.account:
            try:
                daily = self.account.daily_pnl
                if abs(daily) > 5000:
                    return {
                        "type": "risk_alert",
                        "priority": "high",
                        "reason": f"日盈亏 ¥{daily:.0f}",
                        "chain": ["strategy_eval", "trade_execute" if daily < -3000 else "send_notification"],
                    }
            except: pass
        
        # 规则5: 定时巡检 (每5分钟)
        last_hc = self.last_check.get("health", 0)
        if time.time() - last_hc > 300:
            self.last_check["health"] = time.time()
            return {
                "type": "health_check",
                "priority": "low",
                "reason": "定时健康巡检",
                "chain": ["system_monitor", "connection_health"],
            }
        
        return None
    
    def _act(self, action, now):
        """执行能力链"""
        chain = action.get("chain", [])
        results = []
        L.info(f"🧠 执行链 [{action.get('priority','normal')}]: {' → '.join(chain)}")
        
        for step in chain:
            try:
                r = {"step": step, "ok": True}
                
                if step == "send_notification" and self.trader:
                    self.trader.send_notification("GBT大脑", action.get("reason", ""))
                
                elif step == "connection_health":
                    try:
                        from gbt.mcp import get_mcp, call_mcp
                        mcp = get_mcp()
                        total, ok_count, down_list = 0, 0, []
                        for name in list(mcp._s.keys()):
                            try:
                                total += 1
                                result = call_mcp(name, "status", timeout=5)
                                if result.ok:
                                    ok_count += 1
                                else:
                                    down_list.append(name)
                            except: pass
                        r["detail"] = f"{ok_count}/{total} 在线"
                        r["down"] = down_list
                        if ok_count < total:
                            L.warning(f"🧠 连接健康: {ok_count}/{total}")
                            # 尝试自动恢复: 刷新MCP配置
                            if down_list:
                                try:
                                    mcp.refresh()
                                    L.info(f"🧠 MCP配置已刷新，尝试恢复 {len(down_list)} 个断连")
                                    r["recovery"] = "mcp.refresh() 已执行"
                                except Exception as re:
                                    r["recovery"] = f"刷新失败: {re}"
                            # 唤醒守夜人自动修复
                            if self.watcher:
                                try:
                                    self.watcher._add_alert("connections", "warn",
                                        f"大脑检测到{len(down_list)}个MCP断连需要修复",
                                        "; ".join(down_list[:5]))
                                except: pass
                    except: r["ok"] = False
                
                elif step == "log_analysis":
                    try:
                        import os
                        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
                        issues = []
                        if os.path.isdir(log_dir):
                            for f in os.listdir(log_dir)[:5]:
                                if f.endswith((".log", ".txt")):
                                    fp = os.path.join(log_dir, f)
                                    try:
                                        with open(fp, "r", encoding="utf-8", errors="replace") as lf:
                                            tail = "".join(lf.readlines()[-10:])
                                        if "ERROR" in tail or "error" in tail or "CRITICAL" in tail:
                                            issues.append(f"{f}: 发现异常")
                                    except: pass
                        r["detail"] = f"扫描{len(issues)}个异常日志" if issues else "日志正常"
                        r["issues"] = issues
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:80]
                
                elif step == "system_monitor" and self.watcher:
                    ws = self.watcher.get_status()
                    issues = sum(1 for m in ws.get("monitors",{}).values()
                               if m.get("status") in ("warn","critical","error"))
                    r["detail"] = f"{issues} 问题"
                    self.last_check["health"] = time.time()
                
                elif step == "stock_analyze" and self.trader and self.account:
                    for code in list(self.account.positions.keys())[:2]:
                        try:
                            q = self.trader.fetch_quote([code])
                            if code in q:
                                sig = self.trader.analyze_with_ai(code, q[code])
                                r[f"signal_{code}"] = f"{sig.action} {sig.confidence}%"
                        except: pass
                
                results.append(r)
            except Exception as e:
                L.error(f"🧠 执行失败 [{step}]: {e}")
                results.append({"step": step, "ok": False, "error": str(e)[:100]})
        
        with self._lock:
            self.context.appendleft({
                "time": now.strftime("%H:%M:%S"),
                "action": action["type"],
                "priority": action.get("priority", "normal"),
                "reason": action.get("reason", ""),
                "results": results
            })
            self.decisions.appendleft(action)
    
    def get_status(self):
        return {
            "running": self.running,
            "heartbeat": {
                "count": self._beat_count,
                "last": datetime.fromtimestamp(self._last_beat).strftime("%H:%M:%S"),
                "interval": self._beat_interval
            },
            "triggers": dict(self.triggers),
            "decisions": list(self.decisions)[:20],
            "context": list(self.context)[:10],
            "last_checks": self.last_check,
            "capabilities": self.capabilities
        }


brain = AutonomousBrain()
