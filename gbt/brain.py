"""
brain.py — GBT 自主AI大脑 v3
事件驱动心跳 + 外部触发唤醒 + 自适应感知
不等待用户指令，不靠sleep死等，真正主动干活
"""
import os, sys, time, threading, json, logging, re
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Brain")

from gbt.router import router as _router


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
            "stock_analyze": ["trader", "account"],
            "market_scan": ["trader"],
            "strategy_eval": ["trader", "account"],
            "trade_execute": ["trader", "account"],
            "send_notification": ["trader"],
            "connection_health": [],
            "log_analysis": [],
            "system_monitor": ["watcher"],
        }
        # 智能路由器引用
        self.router = None  # 由外部注入
        self.protocol = None  # 执行协议(由外部注入)
        # MCP 实例（延迟初始化）
        self.mcp = None
        # 守夜人 Agent（延迟初始化）
        self.watcher_agent = None
        # Persistent logging
        self._log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "brain.log")
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

    # ── MCP 懒加载 ──
    def _ensure_mcp(self):
        """延迟获取 MCP 单例，避免循环导入"""
        if self.mcp is not None:
            return
        try:
            from gbt.mcp import get_mcp
            self.mcp = get_mcp()
            L.debug(f"MCP 已连接: {len(self.mcp._s)} 个服务")
        except Exception as e:
            L.error(f"MCP 初始化失败: {e}")
            self.mcp = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return {"ok": False, "msg": "大脑已在运行"}
        self.running = True
        self._heartbeat_event.clear()

        # 延迟初始化 MCP
        self._ensure_mcp()

        self.thread = threading.Thread(target=self._brain_loop, daemon=True)
        self.thread.start()

        # 🦉 启动守夜人Agent（独立第二Agent，只读监控不参与改动）
        try:
            from gbt.watcher_agent import get_watcher_agent
            self.watcher_agent = get_watcher_agent(main_brain=self)
            if not self.watcher_agent.running:
                self.watcher_agent.start(main_brain=self)
            self._wa_thread = threading.Thread(target=self._watcher_agent_loop, daemon=True)
            self._wa_thread.start()
            L.info("🦉 守夜人Agent已同步启动")
        except Exception as e:
            L.warning(f"守夜人Agent启动失败: {e}")
            self.watcher_agent = None

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
                L.error(f"大脑循环异常: {e}", exc_info=True)
                self._heartbeat_event.wait(timeout=10)

    def _sense(self, now, is_trading, triggered):
        """感知环境 — 全部非阻塞读取，不直接轮询 MCP/API"""
        p = {
            "time": now.strftime("%H:%M:%S"),
            "is_trading": is_trading,
            "triggered": triggered,
            "alerts": [],
            "connections": {},
            "market_snapshot": {},
            "account_status": {},
        }

        # 1. 守夜人告警 — 读缓存（不用 get_status 避免锁竞争阻塞主循环）
        if self.watcher:
            try:
                for name, st in self.watcher.monitor_status.items():
                    if st.get("status") in ("critical", "error"):
                        p["alerts"].append({
                            "source": name, "level": "critical",
                            "detail": st.get("details", ""),
                            "last": st.get("last_check", "")
                        })
                # 连接状态从 watcher 缓存读（watcher 每 30s 刷新）
                conn_cache = self.watcher.monitor_status.get("connections", {})
                if isinstance(conn_cache, dict) and conn_cache.get("status"):
                    p["connections"] = conn_cache.get("details", {})
                    if isinstance(p["connections"], list):
                        p["connections_down"] = len(p["connections"])
            except Exception as e:
                L.warning(f"感知连接状态失败: {e}")

        # 2. 市场快照
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
            except Exception as e:
                L.warning(f"市场快照获取失败: {e}")

        # 3. 账户
        if self.account:
            try:
                p["account_status"] = {
                    "cash": self.account.cash,
                    "positions": len(self.account.positions),
                    "daily_pnl": self.account.daily_pnl,
                    "total_pnl": self.account.total_pnl
                }
            except Exception as e:
                L.warning(f"账户状态读取失败: {e}")

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
            except Exception as e:
                L.error(f"账户风控检查失败: {e}")

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

        # 默认：无信号 — 返回标准监控决策，绝不返回 None
        return {"action": "monitor", "priority": "low", "reason": "no_signal"}

    def _act(self, action, now):
        """执行能力链"""
        chain = action.get("chain", [])
        results = []
        L.info(f"🧠 执行链 [{action.get('priority','normal')}]: {' → '.join(chain)}")

        for step in chain:
            try:
                r = {"step": step, "ok": True}

                if step == "send_notification" and self.trader:
                    try:
                        self.trader.send_notification("GBT大脑", action.get("reason", ""))
                    except Exception as e:
                        L.error(f"发送通知失败: {e}")
                        r["ok"] = False
                        r["error"] = str(e)[:100]

                elif step == "connection_health":
                    # ⚡ 从 watcher 缓存读连接状态 + MCP 动态计数
                    try:
                        self._ensure_mcp()
                        conn_cache = {}
                        if self.watcher:
                            conn_cache = self.watcher.monitor_status.get("connections", {})
                        down_list = conn_cache.get("details", []) if isinstance(conn_cache, dict) else []
                        # 从 MCP 实例动态获取服务总数
                        total = len(self.mcp._s) if self.mcp else 0
                        ok_count = total - len(down_list) if isinstance(down_list, list) else total
                        r["detail"] = f"{ok_count}/{total} 在线" if ok_count == total else f"{ok_count}/{total} 断连: {', '.join(down_list[:3])}"
                        r["down"] = down_list if isinstance(down_list, list) else []
                        if ok_count < total:
                            L.warning(f"🧠 连接健康(缓存): {ok_count}/{total}")
                            # MCP 配置刷新（非阻塞）
                            try:
                                if down_list and self.mcp:
                                    self.mcp.refresh()
                                    L.info(f"🧠 MCP配置已刷新")
                                    r["recovery"] = "mcp.refresh() 已执行"
                            except Exception as re_exc:
                                L.error(f"MCP 刷新失败: {re_exc}")
                                r["recovery"] = f"刷新失败: {re_exc}"
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:100]
                        L.error(f"连接健康检查失败: {e}")

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
                                    except Exception as e:
                                        L.warning(f"日志扫描跳过 {f}: {e}")
                        r["detail"] = f"扫描{len(issues)}个异常日志" if issues else "日志正常"
                        r["issues"] = issues
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:80]
                        L.error(f"日志分析失败: {e}")

                elif step == "system_monitor" and self.watcher:
                    try:
                        ws = self.watcher.get_status()
                        issues = sum(1 for m in ws.get("monitors",{}).values()
                                   if m.get("status") in ("warn","critical","error"))
                        r["detail"] = f"{issues} 问题"
                        self.last_check["health"] = time.time()
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:100]
                        L.error(f"系统监控失败: {e}")

                elif step == "stock_analyze" and self.trader and self.account:
                    for code in list(self.account.positions.keys())[:2]:
                        try:
                            q = self.trader.fetch_quote([code])
                            if code in q:
                                sig = self.trader.analyze_with_ai(code, q[code])
                                r[f"signal_{code}"] = f"{sig.action} {sig.confidence}%"
                        except Exception as e:
                            L.warning(f"个股分析失败 {code}: {e}")
                            r[f"error_{code}"] = str(e)[:80]

                elif step == "market_scan" and self.trader:
                    try:
                        wl = getattr(self.trader, 'watchlist', []) or []
                        scanned = []
                        for item in wl[:10]:
                            try:
                                code = item.get('code','') or item if isinstance(item,str) else ''
                                if code:
                                    q = self.trader.fetch_quote([code])
                                    if code in q:
                                        chg = q[code].get('pct_change', 0) or 0
                                        if abs(chg) > 2:
                                            scanned.append(f"{code}({chg:+.1f}%)")
                            except Exception as e:
                                L.warning(f"市场扫描跳过 {code}: {e}")
                        r["detail"] = f"扫描{len(wl)}只, 异动{len(scanned)}只"
                        r["anomalies"] = scanned
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:80]
                        L.error(f"市场扫描失败: {e}")

                elif step == "strategy_eval" and self.trader and self.account:
                    try:
                        evals = []
                        for code in list(self.account.positions.keys())[:3]:
                            try:
                                q = self.trader.fetch_quote([code])
                                if code in q:
                                    signal = self.trader.analyze_with_ai(code, q[code])
                                    if signal:
                                        decision = self.trader.decide_trade(signal)
                                        evals.append({"code": code, "signal": signal.action or "hold",
                                            "confidence": signal.confidence, "decision": decision[:100] if decision else "no_decision"})
                            except Exception as e:
                                L.warning(f"策略评估失败 {code}: {e}")
                        r["detail"] = f"评估{len(evals)}只持仓"
                        r["evaluations"] = evals[:5]
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:80]
                        L.error(f"策略评估失败: {e}")

                elif step == "trade_execute" and self.trader and self.account:
                    try:
                        executed = []
                        for code in list(self.account.positions.keys())[:2]:
                            try:
                                q = self.trader.fetch_quote([code])
                                if code in q:
                                    signal = self.trader.analyze_with_ai(code, q[code])
                                    if not signal:
                                        continue
                                    decision = self.trader.decide_trade(signal)
                                    price = q[code].get('price', 0) if isinstance(q[code], dict) else getattr(q[code], 'price', 0)
                                    pos = self.account.positions.get(code)
                                    shares = getattr(pos, 'shares', 0) if pos else 0
                                    if signal.action == "sell" and signal.confidence >= 70 and shares > 0:
                                        self.trader.execute_trade(code, "sell", shares=shares, price=price)
                                        # 同步更新模拟账户
                                        acct_result = self.account.sell(code, shares, price)
                                        trade_pnl = acct_result.get("pnl", 0) if isinstance(acct_result, dict) else 0
                                        executed.append(f"{code}:SELL PnL={trade_pnl}")
                                    elif signal.action == "buy" and signal.confidence >= 75:
                                        buy_shares = max(100, int(self.account.cash * 0.05 / max(price, 0.01) / 100) * 100)
                                        if buy_shares * price <= self.account.cash:
                                            self.trader.execute_trade(code, "buy", shares=buy_shares, price=price)
                                            # 同步更新模拟账户
                                            self.account.buy(code, signal.name if hasattr(signal, 'name') else code, buy_shares, price)
                                            executed.append(f"{code}:BUY {buy_shares}股 @ {price}")
                                        else:
                                            executed.append(f"{code}:SKIP 资金不足")
                            except Exception as e:
                                L.warning(f"交易执行跳过 {code}: {e}")
                        r["detail"] = f"执行{len(executed)}笔" if executed else "无交易"
                        r["executed"] = executed
                    except Exception as e:
                        r["ok"] = False
                        r["error"] = str(e)[:80]
                        L.error(f"交易执行失败: {e}")

                results.append(r)
            except Exception as e:
                L.error(f"🧠 执行失败 [{step}]: {e}", exc_info=True)
                results.append({"step": step, "ok": False, "error": str(e)[:100]})

        with self._lock:
            entry = {
                "time": now.strftime("%H:%M:%S"),
                "action": action.get("type", action.get("action", "unknown")),
                "priority": action.get("priority", "normal"),
                "reason": action.get("reason", ""),
                "results": results
            }
            self.context.appendleft(entry)
            self.decisions.appendleft(action)
            # Persistent log
            try:
                with open(self._log_path, "a", encoding="utf-8") as lf:
                    lf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as le:
                L.error(f"无法写入决策日志: {le}")

    def _watcher_agent_loop(self):
        """守夜人Agent独立心跳循环"""
        time.sleep(15)  # 等大脑先稳定
        while self.running and self.watcher_agent:
            try:
                result = self.watcher_agent.heartbeat()
                if result.get('findings', 0) > 0:
                    L.info(f"🦉 守夜人心跳#{result['heartbeat']}: {result['findings']}项发现")
            except Exception as e:
                L.error(f"守夜人Agent心跳异常: {e}")
            time.sleep(30)  # 每30秒心跳

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
            "capabilities": self.capabilities,
            "router_caps": len(self.router.capabilities) if self.router else 0,
            "watcher_agent": self.watcher_agent.get_status() if self.watcher_agent else None
        }

    def route_intent(self, text: str) -> dict:
        """智能路由用户意图 → 协议链路执行 (7阶段)"""
        if not self.router:
            return {"routed": False, "error": "路由器未注入"}
        # 优先走协议链路 (含预检+验证+错误分级)
        if self.protocol:
            return self.router.route_protocol(text, source="user")
        return self.router.route(text)

    def get_capability_context(self) -> str:
        """获取能力上下文文本 (供LLM推理使用)"""
        if not self.router:
            return ""
        ctx = self.router.get_capability_context()
        ctx += "\n\n**重要**: 当用户请求匹配以上任一能力时，请直接使用该能力。"
        ctx += "\n你是GBT的AI大脑，你拥有上述工具，可以实际执行操作，不仅仅是建议。"
        return ctx


# 模块级单例（保持向后兼容）
brain = AutonomousBrain()


# ═══════════════════════════════════════════════════════════════
# 沙盒验证闭环 (python -m gbt.brain 或 python gbt/brain.py)
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  GBT Brain — 沙盒验证闭环")
    print("=" * 60)

    # 配置日志以便观察
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── 构造模拟依赖 ──
    class MockQuote:
        def __init__(self, code, price, change_pct):
            self.code = code
            self.price = price
            self.change_pct = change_pct
            self.action = "hold"
            self.confidence = 50

    class MockTrader:
        def __init__(self):
            self.watchlist = [
                {"code": "000001", "name": "平安银行"},
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000858", "name": "五粮液"},
            ]
        def fetch_watchlist(self):
            return {
                "000001": MockQuote("000001", 12.50, 1.2),
                "600519": MockQuote("600519", 1680.0, -0.8),
                "000858": MockQuote("000858", 145.0, 2.5),
            }
        def fetch_quote(self, codes):
            return {c: {"code": c, "price": 50.0, "pct_change": 0.5} for c in codes}
        def analyze_with_ai(self, code, quote):
            return MockQuote(code, 50.0, 0.5)
        def decide_trade(self, signal):
            return "hold: 信号不足"
        def execute_trade(self, code, action, shares=0, price=0):
            pass
        def send_notification(self, title, msg):
            pass

    class MockAccount:
        def __init__(self):
            self.cash = 100000.0
            self.positions = {}
            self.daily_pnl = 0.0
            self.total_pnl = 0.0
        def sell(self, code, shares, price):
            return {"pnl": 0}
        def buy(self, code, name, shares, price):
            pass

    class MockWatcher:
        def __init__(self):
            self.monitor_status = {
                "connections": {"status": "ok", "details": []},
                "network": {"status": "ok", "details": "", "last_check": ""},
                "process": {"status": "ok", "details": "", "last_check": ""},
            }
        def get_status(self):
            return {"monitors": {}}

    # ── Mock MCP（模拟动态服务计数） ──
    class MockMCPServer:
        def __init__(self, name):
            self.name = name

    class MockMCP:
        def __init__(self, server_count=19):
            self._s = {f"srv_{i}": MockMCPServer(f"srv_{i}") for i in range(server_count)}
        def refresh(self):
            pass

    # Monkey-patch get_mcp 以避免真实 MCP 配置加载
    _mock_mcp_instance = MockMCP(7)  # 7 个模拟服务
    import gbt.mcp as _mcp_mod
    _orig_get_mcp = _mcp_mod.get_mcp
    _mcp_mod.get_mcp = lambda: _mock_mcp_instance

    print("\n[1] 创建 Brain 实例...")
    trader = MockTrader()
    account = MockAccount()
    watcher = MockWatcher()

    br = AutonomousBrain(trader=trader, watcher=watcher, account=account)
    assert br.trader is not None, "trader 未注入"
    assert br.mcp is None, "MCP 应延迟加载"
    print("    ✅ Brain 实例创建成功（MCP 延迟加载）")

    print("\n[2] 模拟感知 → 思考 → 行动 循环 (3 轮)...")
    from datetime import datetime as dt
    now = dt.now()

    for round_num in range(1, 4):
        print(f"\n   --- 第 {round_num} 轮 ---")

        # 感知
        p = br._sense(now, is_trading=False, triggered=False)
        assert "alerts" in p, "感知结果缺少 alerts"
        assert "market_snapshot" in p, "感知结果缺少 market_snapshot"
        print(f"    ✅ 感知完成: alerts={len(p['alerts'])}, snapshot={p.get('market_snapshot',{}).get('total',0)}只")

        # 思考 → 决策
        action = br._think(p, now, is_trading=False, triggered=False)
        assert action is not None, "❌ 决策返回了 None!"
        assert "action" in action or "type" in action, "决策缺少 action/type 字段"
        print(f"    ✅ 决策: type={action.get('type', action.get('action'))}, priority={action.get('priority')}, reason={action.get('reason')}")

        # 行动
        br._act(action, now)
        print(f"    ✅ 行动完成")

    print("\n[3] 验证 ping() 唤醒...")
    br.running = True
    br._heartbeat_event.clear()
    br.ping("test", "沙盒验证")
    assert br._heartbeat_event.is_set(), "❌ ping() 未设置心跳事件!"
    assert "test" in br.triggers, "❌ ping() 未记录触发器!"
    assert br.triggers["test"]["count"] == 1, f"❌ 触发器计数错误: {br.triggers['test']['count']}"
    print(f"    ✅ ping() 唤醒成功: triggers={dict(br.triggers)}")

    print("\n[4] 验证空决策不返回 None...")
    p_empty = {"time": "12:00:00", "is_trading": False, "triggered": False, "alerts": [], "connections": {}, "market_snapshot": {}, "account_status": {}}
    action_empty = br._think(p_empty, now, is_trading=False, triggered=False)
    assert action_empty is not None, "❌ 空决策返回了 None!"
    assert action_empty.get("action") == "monitor" or action_empty.get("reason") == "no_signal", \
        f"❌ 空决策内容错误: {action_empty}"
    print(f"    ✅ 空决策: {action_empty}")

    print("\n[5] 验证 MCP 计数动态获取...")
    br._ensure_mcp()
    mcp_total = len(br.mcp._s) if br.mcp else 0
    assert mcp_total == 7, f"❌ MCP 计数应为 7，实际: {mcp_total}"
    print(f"    ✅ MCP 动态计数: {mcp_total} 个服务")

    print("\n[6] 验证异常路径有日志...")
    # 模拟 trader 为 None 时的容错
    br_no_trader = AutonomousBrain(trader=None, watcher=None, account=None)
    p_no_trader = br_no_trader._sense(now, is_trading=True, triggered=False)
    assert p_no_trader["market_snapshot"] == {}, "无 trader 时快照应为空"
    print(f"    ✅ 无 trader 时感知容错正常")

    # 模拟 _think 异常场景
    action_fallback = br_no_trader._think({"time": "12:00", "is_trading": True, "triggered": False, "alerts": []}, now, is_trading=True, triggered=False)
    assert action_fallback is not None, "❌ 异常场景下 _think 返回了 None"
    print(f"    ✅ _think 异常容错: {action_fallback}")

    # 触发 ping 后决策
    br.running = True
    br._heartbeat_event.set()
    p_pinged = {"time": "12:00:00", "is_trading": False, "triggered": True,
                "alerts": [{"source": "network", "level": "critical", "detail": "test alert", "last": "12:00"}],
                "connections": {}, "market_snapshot": {}, "account_status": {}}
    action_pinged = br._think(p_pinged, now, is_trading=False, triggered=True)
    assert action_pinged["priority"] == "critical", f"❌ ping 唤醒后优先级应为 critical: {action_pinged}"
    print(f"    ✅ ping 唤醒决策: {action_pinged}")

    # 恢复 get_mcp
    _mcp_mod.get_mcp = _orig_get_mcp

    print("\n" + "=" * 60)
    print("  ✅ 所有验证通过 — brain.py 沙盒闭环正常")
    print("=" * 60)
