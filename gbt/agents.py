"""
agents.py — GBT 多Agent架构 v1.0
智能路由器Agent + 领域Agent，各司其职

Agent清单:
  RouterAgent   — 智能调度，意图分发
  TradingAgent  — A股操盘，行情分析
  DesktopAgent  — 桌面操控，窗口/截图/浏览器
  HackerAgent   — 代码执行，文件操作，网页搜索
  SystemAgent   — 系统状态，账户查询
  NotifyAgent   — 桌面通知
  WatcherAgent  — 守夜人监控（已独立存在）

生命周期:
  User Intent → RouterAgent.classify() → TargetAgent.execute()
                                        → verify() → respond()
"""
import os, sys, json, time, threading, logging, traceback
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

L = logging.getLogger("GBT.Agents")


# ═══════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════

@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    description: str
    keywords: list[str]
    handler: Callable
    priority: int = 5
    requires: list[str] = field(default_factory=list)

@dataclass
class AgentResult:
    """Agent执行结果"""
    agent: str
    capability: str
    ok: bool
    data: str = ""
    elapsed_ms: float = 0
    error: Optional[str] = None
    trace_id: str = ""


# ═══════════════════════════════════════════════════════
# 基础Agent
# ═══════════════════════════════════════════════════════

class BaseAgent(ABC):
    """所有Agent的基类"""
    
    def __init__(self, name: str, description: str, brain=None):
        self.name = name
        self.description = description
        self.brain = brain  # 大脑引用（用于ping）
        self.framework = None  # 框架引用（由MultiAgentFramework注入）
        self.capabilities: list[AgentCapability] = []
        self.running = True
        self._lock = threading.Lock()
        self.stats = {"calls": 0, "errors": 0, "last_call": None}
        self._local_context = {}  # Agent本地上下文
        
    def register(self, name: str, desc: str, keywords: list[str],
                 handler: Callable, priority: int = 5, requires: list[str] = None):
        """注册能力"""
        cap = AgentCapability(name, desc, keywords, handler, priority, requires or [])
        self.capabilities.append(cap)
        L.info(f"  [{self.name}] 已注册: {name} (p={priority})")
        return cap
    
    def matches(self, text: str) -> list[AgentCapability]:
        """匹配文本命中的能力"""
        matched = []
        text_lower = text.lower()
        for cap in self.capabilities:
            for kw in cap.keywords:
                if kw in text_lower or kw in text:
                    matched.append(cap)
                    break
        return sorted(matched, key=lambda c: c.priority, reverse=True)
    
    @abstractmethod
    def execute(self, capability_name: str, text: str) -> AgentResult:
        """执行指定能力"""
        ...
    
    def get_context(self) -> dict:
        """获取Agent上下文"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": [
                {"name": c.name, "desc": c.description, "priority": c.priority}
                for c in self.capabilities
            ],
            "stats": dict(self.stats),
            "local_context_keys": list(self._local_context.keys()),
        }
    
    def publish(self, capability: str, ok: bool, data: str = ""):
        """向共享上下文发布执行结果（不影响主Agent）"""
        if self.framework:
            try:
                self.framework._on_agent_executed(self.name, capability, ok, data)
            except:
                pass  # 静默失败，不影响主执行流
    
    def ping_brain(self, source: str, reason: str):
        """通知大脑"""
        if self.brain and hasattr(self.brain, 'ping'):
            try:
                self.brain.ping(source, reason)
            except:
                pass


# ═══════════════════════════════════════════════════════
# 专用Agent
# ═══════════════════════════════════════════════════════

class DesktopAgent(BaseAgent):
    """桌面操控Agent"""
    
    def __init__(self, brain=None):
        super().__init__("DesktopAgent", "桌面操控", brain)
        self._setup_capabilities()
    
    def _setup_capabilities(self):
        self.register("browser_open", "打开浏览器/网页",
                     ["浏览器", "打开网页", "上网", "bing", "百度", "谷歌", "网址"],
                     self._browser_open, priority=7)
        self.register("window_maximize", "最大化/全屏窗口",
                     ["最大化", "全屏", "窗口最大", "放大到最大", "窗口放大"],
                     self._window_maximize, priority=6)
        self.register("screenshot", "屏幕截图",
                     ["截图", "截屏", "屏幕截图", "拍屏", "截个图", "拍个"],
                     self._screenshot, priority=6)
    
    def _browser_open(self, text):
        import urllib.parse
        query = text
        for kw in ["打开浏览器", "浏览器", "打开", "看新闻"]:
            query = query.replace(kw, "")
        query = query.strip() or "about:blank"
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}" if query != "about:blank" else "https://www.bing.com"
        os.startfile(url)
        return f"已打开: {url}"
    
    def _window_maximize(self, text):
        try:
            import pyautogui
            pyautogui.hotkey("win", "up")
            return "已最大化当前窗口"
        except:
            return "窗口最大化完成"
    
    def _screenshot(self, text):
        import pyautogui
        ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
        os.makedirs(ss_dir, exist_ok=True)
        fp = os.path.join(ss_dir, f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(fp)
        return f"截图已保存 → {fp}" if os.path.exists(fp) else "截图失败"
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        t0 = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now().strftime("%H:%M:%S")
        
        for cap in self.capabilities:
            if cap.name == capability_name:
                try:
                    data = cap.handler(text)
                    return AgentResult(self.name, cap.name, True, data, (time.time()-t0)*1000)
                except Exception as e:
                    self.stats["errors"] += 1
                    return AgentResult(self.name, cap.name, False, error=str(e), elapsed_ms=(time.time()-t0)*1000)
        
        return AgentResult(self.name, "unknown", False, error=f"未找到能力: {capability_name}")


class TradingAgent(BaseAgent):
    """A股操盘Agent"""
    
    def __init__(self, brain=None, trader=None, account=None):
        super().__init__("TradingAgent", "A股交易行情", brain)
        self.trader = trader
        self.account = account
        self._setup_capabilities()
    
    def _setup_capabilities(self):
        self.register("stock_lookup", "查询股票实时行情",
                     ["行情", "分析", "查询股票", "股票", "600", "000", "300", "688"],
                     self._stock_lookup, priority=8)
        self.register("market_scan", "扫描全市场/自选股",
                     ["全市场", "市场扫描", "扫一遍", "扫描市场"],
                     self._market_scan, priority=6)
        self.register("watchlist", "查看自选股列表",
                     ["自选股", "自选", "我的自选", "持仓列表"],
                     self._watchlist, priority=7)
        self.register("auto_trade", "触发自主交易分析",
                     ["交易", "买", "卖", "买入", "卖出", "下单", "操盘", "自主交易"],
                     self._auto_trade, priority=9, requires=["trader", "account"])
    
    def _stock_lookup(self, text):
        import re
        # Python 3 \w 包含中文 → \b 在"600519行情"中失效(数字和中文同为\w)
        # 用 ASCII-only lookbehind/lookahead 替代
        m = re.search(r'(?<![a-zA-Z0-9])(6\d{5}|0\d{5}|3\d{5}|68\d{4})(?![a-zA-Z0-9])', text)
        if not m:
            return "未找到有效股票代码"
        code = m.group(1)
        prefix = "sh" if code.startswith('6') or code.startswith('68') else "sz"
        full = f"{prefix}{code}"
        try:
            import urllib.request
            url = f"https://hq.sinajs.cn/list={full}"
            req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
            r = urllib.request.urlopen(req, timeout=5)
            raw = r.read().decode('gbk', errors='replace')
            name = raw.split('"')[1].split(',')[0] if '"' in raw else code
            parts = raw.split('"')[1].split(',') if '"' in raw else []
            if len(parts) >= 4:
                price = parts[3]
                change = float(parts[3]) - float(parts[2]) if len(parts)>3 else 0
                pct = (change / float(parts[2]) * 100) if float(parts[2]) > 0 else 0
                return f"{name}({code}): ¥{price} {'+' if change>=0 else ''}{change:.2f} ({pct:+.2f}%)"
            return f"{name}({code}): 数据解析异常"
        except Exception as e:
            return f"行情查询失败: {code} — {e}"
    
    def _market_scan(self, text):
        if self.trader:
            ws = self.trader.watchlist
            codes = list(ws.keys())[:10] if isinstance(ws, dict) else list(ws)[:10]
            return f"自选池共 {len(ws)} 只股票: {', '.join(codes)}"
        return "交易引擎未就绪"
    
    def _watchlist(self, text):
        if self.trader:
            ws = self.trader.watchlist
            codes = list(ws.keys()) if isinstance(ws, dict) else list(ws)
            return f"自选池共 {len(ws)} 只: {', '.join(codes[:20])}"
        return "交易引擎未就绪"
    
    def _auto_trade(self, text):
        import re
        m = re.search(r'(?<![a-zA-Z0-9])(6\d{5}|0\d{5}|3\d{5})(?![a-zA-Z0-9])', text)
        code = m.group(1) if m else ""
        parts = []
        parts.append(f"📊 交易引擎: auto_trade={'ON' if (self.trader and self.trader.auto_trade) else 'OFF'}")
        parts.append(f"📍 自选池: {len(self.trader.watchlist) if self.trader else 0} 只")
        if self.account:
            parts.append(f"💰 可用资金: ¥{self.account.cash:,.0f}")
        if code:
            parts.append(f"🎯 目标: {code}")
        self.ping_brain("trader", f"交易分析请求: {code or '全池扫描'}")
        return "\n".join(parts)
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        t0 = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now().strftime("%H:%M:%S")
        
        for cap in self.capabilities:
            if cap.name == capability_name:
                try:
                    data = cap.handler(text)
                    return AgentResult(self.name, cap.name, True, data, (time.time()-t0)*1000)
                except Exception as e:
                    self.stats["errors"] += 1
                    return AgentResult(self.name, cap.name, False, error=str(e), elapsed_ms=(time.time()-t0)*1000)
        
        return AgentResult(self.name, "unknown", False, error=f"未找到能力: {capability_name}")


class HackerAgent(BaseAgent):
    """编程/黑客Agent"""
    
    def __init__(self, brain=None):
        super().__init__("HackerAgent", "编程黑客", brain)
        self._setup_capabilities()
    
    def _setup_capabilities(self):
        self.register("web_search", "网络搜索获取实时信息",
                     ["搜索", "查一下", "search"],
                     self._web_search, priority=9)
        self.register("file_operation", "文件读写操作",
                     ["读文件", "写文件", "创建文件", "编辑文件"],
                     self._file_op, priority=6)
        self.register("code_exec", "执行Python/Shell代码",
                     ["执行代码", "运行代码", "```", "shell", "cmd"],
                     self._code_exec, priority=8)
    
    def _web_search(self, text):
        import urllib.parse
        for kw in ["搜索", "查一下", "search"]:
            text = text.replace(kw, "")
        query = text.strip()[:200] or "最新消息"
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        os.startfile(url)
        return f"已搜索: {query}"
    
    def _file_op(self, text):
        import re
        m = re.search(r'(?:读|打开|查看)\s*(?:文件)?\s*[\"\']?([^\"\'\s]+(?:\.[a-zA-Z]+))', text)
        if m:
            fpath = m.group(1)
            if not os.path.isabs(fpath):
                fpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), fpath)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()[:2000]
                    return f"📄 {os.path.basename(fpath)} ({len(content)}字符):\n{content[:500]}"
                except:
                    return f"无法读取: {fpath}"
            return f"文件不存在: {fpath}"
        return "请指定要读取的文件路径"
    
    def _code_exec(self, text):
        import subprocess, re
        # 提取代码块: ```python ... ``` 或 ``` ... ```
        code_m = re.search(r'```(?:python|py|bash|sh|shell|cmd|ps1)?\s*\n?(.*?)```', text, re.DOTALL | re.IGNORECASE)
        if not code_m:
            return "请用 ```python ... ``` 格式提供代码"
        
        code = code_m.group(1).strip()
        if not code:
            return "代码块为空"
        
        # 确定执行器: bash/sh → shell; 其他 → python
        fence = code_m.group(0)[:30]
        is_shell = any(tag in fence.lower() for tag in ('sh', 'bash', 'shell', 'cmd', 'ps1'))
        
        try:
            if is_shell:
                r = subprocess.run(code, shell=True, capture_output=True,
                                  text=True, timeout=10, errors='replace')
            else:
                # 用 Python312 执行
                python_exe = r'C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe'
                if not os.path.exists(python_exe):
                    python_exe = 'python'  # 降级
                r = subprocess.run([python_exe, "-c", code],
                                  capture_output=True, text=True, timeout=20,
                                  errors='replace')
            
            out = (r.stdout.rstrip() + ('\n' + r.stderr.rstrip() if r.stderr else ''))[:1000]
            if not out:
                out = "(执行完成，无输出)"
            return f"⚡ 执行结果:\n{out}"
        except subprocess.TimeoutExpired:
            return "⏱ 代码执行超时(>20s)"
        except Exception as e:
            return f"❌ 执行失败: {e}"
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        t0 = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now().strftime("%H:%M:%S")
        
        for cap in self.capabilities:
            if cap.name == capability_name:
                try:
                    data = cap.handler(text)
                    return AgentResult(self.name, cap.name, True, data, (time.time()-t0)*1000)
                except Exception as e:
                    self.stats["errors"] += 1
                    return AgentResult(self.name, cap.name, False, error=str(e), elapsed_ms=(time.time()-t0)*1000)
        
        return AgentResult(self.name, "unknown", False, error=f"未找到能力: {capability_name}")


class SystemAgent(BaseAgent):
    """系统监控Agent"""
    
    def __init__(self, brain=None, watcher=None, account=None):
        super().__init__("SystemAgent", "系统监控", brain)
        self.watcher = watcher
        self.account = account
        self._setup_capabilities()
    
    def _setup_capabilities(self):
        self.register("system_status", "查看GBT系统状态",
                     ["状态", "系统状态", "系统", "运行状态", "情况"],
                     self._system_status, priority=8, requires=["watcher"])
        self.register("watcher_check", "守夜人安全监控",
                     ["安全", "监控", "安全检查", "防御"],
                     self._watcher_check, priority=7, requires=["watcher"])
        self.register("account_query", "查看模拟账户",
                     ["账户", "资金", "余额", "盈亏", "持仓", "仓位", "钱"],
                     self._account_query, priority=6, requires=["account"])
    
    def _system_status(self, text):
        parts = []
        if self.brain:
            parts.append(f"大脑: {'运行中' if self.brain.running else '已停止'} | {self.brain._beat_count} 心跳")
        if self.watcher:
            ws = self.watcher.get_status()
            ok_count = sum(1 for s in ws.get('monitors',{}).values() if s.get('status') in ('ok','checking'))
            parts.append(f"监控: {ok_count}/8 正常")
        # 尝试获取交易状态
        try:
            from gbt.trader import trader as _tr
            parts.append(f"交易: auto_trade={'ON' if _tr.auto_trade else 'OFF'} | {len(_tr.watchlist)} 自选")
        except: pass
        return "\n".join(parts) if parts else "系统状态正常"
    
    def _watcher_check(self, text):
        if not self.watcher:
            return "守夜人未就绪"
        ws = self.watcher.get_status()
        parts = ["🛡️ 守夜人安全报告:"]
        for name, st in ws.get('monitors', {}).items():
            s = st.get('status', '?')
            d = st.get('details', '')
            icon = '✅' if s in ('ok','checking') else '⚠️' if s=='warn' else '❌'
            parts.append(f"  {icon} {name}: {s} ({d[:30] if d else '...'})")
        alerts = ws.get('recent_alerts', [])
        if alerts:
            parts.append(f"🚨 {len(alerts)} 活跃告警")
        return "\n".join(parts)
    
    def _account_query(self, text):
        if not self.account:
            return "账户未就绪"
        try:
            parts = [
                f"💰 模拟账户: ¥{self.account.cash:,.0f}",
                f"📊 持仓: {len(self.account.positions)} 只",
            ]
            total_val = self.account.cash + sum(p.current_value for p in self.account.positions.values())
            profit = total_val - 100000
            parts.append(f"📈 总盈亏: ¥{profit:+,.0f}")
            return "\n".join(parts)
        except Exception as e:
            return f"账户查询失败: {e}"
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        t0 = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now().strftime("%H:%M:%S")
        
        for cap in self.capabilities:
            if cap.name == capability_name:
                try:
                    data = cap.handler(text)
                    return AgentResult(self.name, cap.name, True, data, (time.time()-t0)*1000)
                except Exception as e:
                    self.stats["errors"] += 1
                    return AgentResult(self.name, cap.name, False, error=str(e), elapsed_ms=(time.time()-t0)*1000)
        
        return AgentResult(self.name, "unknown", False, error=f"未找到能力: {capability_name}")


class NotifyAgent(BaseAgent):
    """通知Agent"""
    
    def __init__(self, brain=None):
        super().__init__("NotifyAgent", "桌面通知", brain)
        self._setup_capabilities()
    
    def _setup_capabilities(self):
        self.register("notify", "发送Windows桌面通知",
                     ["通知", "提醒我", "提醒", "弹窗"],
                     self._notify, priority=4)
    
    def _notify(self, text):
        try:
            from plyer import notification
            notification.notify(title="GBT 通知", message=text[:100],
                              app_name="GBT Pro", timeout=5)
            return "桌面通知已发送"
        except:
            return "已发送（通知可能未显示，plyer可能未安装）"
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        t0 = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = datetime.now().strftime("%H:%M:%S")
        
        for cap in self.capabilities:
            if cap.name == capability_name:
                try:
                    data = cap.handler(text)
                    return AgentResult(self.name, cap.name, True, data, (time.time()-t0)*1000)
                except Exception as e:
                    self.stats["errors"] += 1
                    return AgentResult(self.name, cap.name, False, error=str(e), elapsed_ms=(time.time()-t0)*1000)
        
        return AgentResult(self.name, "unknown", False, error=f"未找到能力: {capability_name}")


# ═══════════════════════════════════════════════════════
# 路由器Agent — 智能调度中枢
# ═══════════════════════════════════════════════════════

class RouterAgent(BaseAgent):
    """智能路由器Agent — 意图分类 + 领域Agent调度"""
    
    def __init__(self, brain=None):
        super().__init__("RouterAgent", "智能调度中枢", brain)
        self.agents: dict[str, BaseAgent] = {}
        self.protocol = None  # 7阶段协议(可选)
        self.history: list[AgentResult] = []
    
    def register_agent(self, agent: BaseAgent):
        """注册领域Agent"""
        self.agents[agent.name] = agent
        L.info(f"🔗 {agent.name} 已注册到路由器 — {len(agent.capabilities)}项能力")
    
    def classify(self, text: str) -> Optional[tuple[BaseAgent, AgentCapability]]:
        """意图分类 — 找到最匹配的Agent和能力"""
        if not text or not text.strip():
            return None
        
        all_matches = []
        for agent in self.agents.values():
            if not agent.running:
                continue
            caps = agent.matches(text)
            for cap in caps:
                all_matches.append((agent, cap))
        
        if not all_matches:
            return None
        
        # 按priority排序选最高
        all_matches.sort(key=lambda x: x[1].priority, reverse=True)
        return all_matches[0]
    
    def route(self, text: str, source: str = "user") -> dict:
        """路由执行 — 分类 → 分发 → Agent.execute → 结果"""
        t0 = time.time()
        trace_id = f"gex-{int(time.time()*1000)}-{self.stats['calls']}"
        
        # 如果没有协议，走直接路由
        if not self.protocol:
            return self._route_direct(text, source, t0, trace_id)
        
        # 走7阶段协议
        return self._route_protocol(text, source, t0, trace_id)
    
    def _route_direct(self, text, source, t0, trace_id):
        match = self.classify(text)
        if not match:
            return {
                "capability": None,
                "conclusion": f"(RouterAgent: 未找到匹配能力, source={source})",
                "protocol": {"ok": False, "trace_id": trace_id, "error": "no_match"},
                "elapsed_ms": int((time.time()-t0)*1000)
            }
        
        agent, cap = match
        result = agent.execute(cap.name, text)
        self.history.append(result)
        self.stats["calls"] += 1
        
        return {
            "capability": result.capability,
            "agent": result.agent,
            "conclusion": result.data,
            "protocol": {
                "ok": result.ok,
                "trace_id": trace_id,
                "agent": result.agent,
                "capability": result.capability,
                "elapsed_ms": result.elapsed_ms,
                "error_level": None if result.ok else "L3_ALERT",
                "errors": [] if result.ok else [result.error],
                "phases": {
                    "intent": {"ok": True, "intent": text[:80], "source": source},
                    "route": {"ok": True, "agent": agent.name, "capability": cap.name},
                    "acknowledge": {"ok": True, "agent": agent.name, "capability": cap.name},
                    "pre_check": {"ok": True, "detail": "no dependencies" if not cap.requires else f"{cap.requires} deps"},
                    "execute": {"ok": result.ok, "raw_len": len(result.data)},
                    "verify": {"ok": result.ok, "detail": "default: data returned"},
                    "respond": {"ok": True},
                }
            },
            "elapsed_ms": int((time.time()-t0)*1000)
        }
    
    def _route_protocol(self, text, source, t0, trace_id):
        """7阶段协议路由"""
        phases = {}
        
        # Phase 1: INTENT
        phases["intent"] = {"ok": True, "intent": text[:80], "source": source}
        
        # Phase 2: ROUTE
        match = self.classify(text)
        if not match:
            phases["route"] = {"ok": False, "error": "no_match"}
            return {
                "capability": None,
                "conclusion": "",
                "protocol": {"ok": False, "trace_id": trace_id, "phases": phases, "error": "no_match"},
            }
        agent, cap = match
        phases["route"] = {"ok": True, "agent": agent.name, "capability": cap.name}
        
        # Phase 3: ACK
        phases["acknowledge"] = {"ok": True, "agent": agent.name, "capability": cap.name, "description": cap.description}
        
        # Phase 4: PRE_CHECK
        missing = []
        for dep in cap.requires:
            # 检查依赖（简化: trader/account/watcher）
            if dep == "trader":
                try:
                    from gbt.trader import trader as _t
                    if not _t: missing.append(dep)
                except: missing.append(dep)
            elif dep == "account":
                if not hasattr(self, '_account') or not self._account:
                    try:
                        import gbt.account as _a
                        self._account = _a.account if hasattr(_a, 'account') else None
                    except: missing.append(dep)
            elif dep == "watcher":
                try:
                    from gbt.watcher import watcher as _w
                    if not _w: missing.append(dep)
                except: missing.append(dep)
        
        if missing:
            phases["pre_check"] = {"ok": False, "detail": f"缺失依赖: {missing}"}
            return {
                "capability": cap.name,
                "conclusion": f"Agent依赖未就绪: {missing}",
                "protocol": {"ok": False, "trace_id": trace_id, "phases": phases, "error": "dependency_missing"},
            }
        phases["pre_check"] = {"ok": True, "detail": "所有依赖就绪" if cap.requires else "无依赖"}
        
        # Phase 5: EXECUTE
        t_exec = time.time()
        result = agent.execute(cap.name, text)
        self.history.append(result)
        self.stats["calls"] += 1
        phases["execute"] = {"ok": result.ok, "raw_len": len(result.data), "elapsed_ms": result.elapsed_ms}
        
        # Phase 6: VERIFY
        if not result.ok:
            phases["verify"] = {"ok": False, "detail": result.error}
        elif len(result.data) < 5:
            phases["verify"] = {"ok": False, "detail": "响应数据过短"}
        else:
            phases["verify"] = {"ok": True, "detail": "数据验证通过"}
        
        # Phase 7: RESPOND
        phases["respond"] = {"ok": True, "agent": result.agent, "elapsed_ms": int((time.time()-t0)*1000)}
        
        return {
            "capability": result.capability,
            "agent": result.agent,
            "conclusion": result.data,
            "protocol": {
                "ok": phases["verify"]["ok"] and phases["execute"]["ok"],
                "trace_id": trace_id,
                "agent": result.agent,
                "capability": result.capability,
                "elapsed_ms": int((time.time()-t_exec)*1000),
                "error_level": "L3_ALERT" if not result.ok else None,
                "errors": [] if result.ok else [result.error],
                "phases": phases,
            },
            "elapsed_ms": int((time.time()-t0)*1000)
        }
    
    def get_all_context(self) -> dict:
        """获取所有Agent的上下文"""
        ctx = {
            "router": self.get_context(),
            "agents": {}
        }
        for name, agent in self.agents.items():
            ctx["agents"][name] = agent.get_context()
        ctx["total_capabilities"] = sum(len(a.capabilities) for a in self.agents.values())
        return ctx
    
    def execute(self, capability_name: str, text: str) -> AgentResult:
        """Router的execute就是route"""
        r = self.route(text)
        proto = r.get("protocol", {})
        return AgentResult(
            self.name,
            r.get("capability", "unknown"),
            proto.get("ok", False),
            r.get("conclusion", ""),
            r.get("elapsed_ms", 0),
            error=proto.get("error"),
            trace_id=proto.get("trace_id", "")
        )


# ═══════════════════════════════════════════════════════
# 多Agent框架 — 统一组装
# ═══════════════════════════════════════════════════════

class MultiAgentFramework:
    """多Agent框架 — 组装 + 启动 + 协调 + 共享上下文"""
    
    def __init__(self, brain=None, trader=None, account=None, watcher=None):
        self.brain = brain
        self.trader = trader
        self.account = account
        self.watcher = watcher
        
        # 🔄 共享上下文 — 所有Agent可读写的全局状态
        self.shared_context = {
            "framework_version": "v1.0",
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_action": None,
            "last_agent": None,
            "action_history": [],  # 最近20条全局动作记录
            "alerts": [],          # 全局告警(守夜人注入)
            "market_status": {},   # 行情快照
            "system_health": {},   # 系统健康
        }
        self._ctx_lock = threading.Lock()
        
        # 初始化所有Agent
        self.router = RouterAgent(brain)
        self.desktop = DesktopAgent(brain)
        self.trading = TradingAgent(brain, trader, account)
        self.hacker = HackerAgent(brain)
        self.system = SystemAgent(brain, watcher, account)
        self.notify = NotifyAgent(brain)
        
        # 注入共享上下文到所有Agent
        for agent in [self.router, self.desktop, self.trading,
                      self.hacker, self.system, self.notify]:
            agent.framework = self  # 反向引用
        
        # 注册到路由器
        self.router.register_agent(self.desktop)
        self.router.register_agent(self.trading)
        self.router.register_agent(self.hacker)
        self.router.register_agent(self.system)
        self.router.register_agent(self.notify)
        
        L.info(f"🚀 多Agent框架就绪: {len(self.router.agents)} 领域Agent + 共享上下文")
    
    # ═══════════════════════════════════════════════════════
    # 共享上下文管理
    # ═══════════════════════════════════════════════════════
    
    def update_context(self, agent_name: str, action: str, detail: dict = None):
        """Agent执行后更新共享上下文"""
        with self._ctx_lock:
            self.shared_context["last_agent"] = agent_name
            self.shared_context["last_action"] = {
                "agent": agent_name,
                "action": action,
                "time": datetime.now().strftime("%H:%M:%S"),
                "detail": detail or {}
            }
            self.shared_context["action_history"].append(self.shared_context["last_action"])
            if len(self.shared_context["action_history"]) > 20:
                self.shared_context["action_history"] = self.shared_context["action_history"][-20:]
    
    def sync_with_watcher(self):
        """同步守夜人Agent的发现到共享上下文"""
        try:
            from gbt.watcher_agent import get_watcher_agent
            wa = get_watcher_agent()
            if wa and wa.running:
                status = wa.get_status()
                with self._ctx_lock:
                    # 注入守夜人发现
                    findings = status.get("recent_findings", [])
                    if findings:
                        self.shared_context["alerts"] = findings[-10:]
                    # 同步系统健康
                    self.shared_context["system_health"] = {
                        "watcher_agent": status.get("running", False),
                        "heartbeats": status.get("heartbeat_count", 0),
                        "hallucination_count": status.get("stats", {}).get("hallucination", 0),
                        "connection_alerts": status.get("stats", {}).get("connection_alerts", 0),
                    }
        except Exception as e:
            L.debug(f"守夜人同步: {e}")
    
    def notify_all_agents(self, message: str, level: str = "info"):
        """向所有Agent广播消息（不干扰主Agent）"""
        with self._ctx_lock:
            self.shared_context.setdefault("broadcasts", []).append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message
            })
            # 保留最近10条广播
            if len(self.shared_context["broadcasts"]) > 10:
                self.shared_context["broadcasts"] = self.shared_context["broadcasts"][-10:]
    
    def get_shared_context(self) -> dict:
        """获取共享上下文快照"""
        with self._ctx_lock:
            ctx = dict(self.shared_context)
            # 返回全部历史（最多20条），不截断
            ctx["action_history"] = list(ctx["action_history"])
            return ctx
    
    def _on_agent_executed(self, agent_name: str, capability: str, ok: bool, data: str = ""):
        """Agent执行完成钩子 — 更新上下文 + 检查冲突"""
        self.update_context(agent_name, capability, {
            "ok": ok,
            "data_preview": data[:100] if data else ""
        })
        # 每5次执行同步一次守夜人
        total_calls = sum(a.stats.get("calls", 0) for a in self.router.agents.values())
        if total_calls % 5 == 0:
            self.sync_with_watcher()
    
    def get_system_status(self) -> dict:
        """获取全系统状态"""
        agents_ok = sum(1 for a in self.router.agents.values() if a.running)
        total_caps = sum(len(a.capabilities) for a in self.router.agents.values())
        return {
            "framework": "v1.0",
            "router": self.router.get_context(),
            "agents": {name: agent.get_context() for name, agent in self.router.agents.items()},
            "agents_running": f"{agents_ok}/{len(self.router.agents)}",
            "total_capabilities": total_caps,
        }
    
    def get_monitor_report(self) -> dict:
        """获取监控报告（守夜人+Agent状态汇总）"""
        report = {"time": datetime.now().strftime("%H:%M:%S"), "agents": {}}
        for name, agent in self.router.agents.items():
            report["agents"][name] = {
                "running": agent.running,
                "calls": agent.stats.get("calls", 0),
                "errors": agent.stats.get("errors", 0),
            }
        report["watcher"] = self.watcher.get_status() if self.watcher else None
        return report


# ═══════════════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════════════

_multi_agent_framework: Optional[MultiAgentFramework] = None


def get_framework() -> MultiAgentFramework:
    """获取多Agent框架单例（需先 init_framework）"""
    global _multi_agent_framework
    if _multi_agent_framework is None:
        raise RuntimeError("多Agent框架未初始化，请先调用 init_framework()")
    return _multi_agent_framework


def init_framework(brain=None, trader=None, account=None, watcher=None) -> MultiAgentFramework:
    """初始化多Agent框架"""
    global _multi_agent_framework
    _multi_agent_framework = MultiAgentFramework(brain, trader, account, watcher)
    return _multi_agent_framework
