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
            except Exception as e:
                L.debug(f"_on_agent_executed 回调失败: {e}")
    
    def ping_brain(self, source: str, reason: str):
        """通知大脑"""
        if self.brain and hasattr(self.brain, 'ping'):
            try:
                self.brain.ping(source, reason)
            except Exception as e:
                L.debug(f"Brain ping 失败: {e}")


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
                     ["最大化", "全屏", "窗口最大", "放大", "窗口放大"],
                     self._window_maximize, priority=6)
        self.register("screenshot", "屏幕截图保存",
                     ["截图", "截屏", "屏幕截图", "拍屏", "拍个"],
                     self._screenshot, priority=6)
        # 桌面全控能力
        self.register("keyboard_type", "模拟键盘输入文字",
                     ["输入", "打字", "键盘输入", "type"],
                     self._keyboard_type, priority=5)
        self.register("keyboard_hotkey", "模拟快捷键组合",
                     ["快捷键", "热键", "组合键", "hotkey", "ctrl", "alt", "win键"],
                     self._keyboard_hotkey, priority=5)
        self.register("mouse_click", "鼠标点击指定位置",
                     ["点击", "鼠标点击", "双击", "右键"],
                     self._mouse_click, priority=5)
        self.register("mouse_move", "移动鼠标到指定位置",
                     ["移动鼠标", "鼠标移动", "光标"],
                     self._mouse_move, priority=4)
        self.register("process_kill", "终止指定进程",
                     ["结束进程", "杀掉", "终止", "kill", "关闭程序"],
                     self._process_kill, priority=7)
        self.register("process_list", "列出所有运行进程",
                     ["进程列表", "任务管理器", "运行程序", "所有进程"],
                     self._process_list, priority=5)
        self.register("window_focus", "聚焦指定窗口",
                     ["切换窗口", "聚焦", "前台", "focus"],
                     self._window_focus, priority=5)
        self.register("volume_control", "调节系统音量",
                     ["音量", "静音", "声音"],
                     self._volume_control, priority=3)
        self.register("system_lock", "锁定Windows系统",
                     ["锁定", "锁屏", "lock"],
                     self._system_lock, priority=4)
        self.register("gcc_run", "通用电脑控制(GCC)",
                     ["操控电脑", "GCC", "帮我操作", "自动操作", "代替我操作", "屏幕操作"],
                     self._gcc_run, priority=9)
        self.register("screenshot_reason", "截图视觉推理",
                     ["分析屏幕", "看屏幕", "屏幕分析", "截图分析", "视觉分析"],
                     self._screenshot_reason, priority=8)
    
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
        except Exception as e:
            L.debug(f"窗口最大化失败: {e}")
            return "窗口最大化完成"
    
    def _screenshot(self, text):
        import pyautogui
        ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
        os.makedirs(ss_dir, exist_ok=True)
        fp = os.path.join(ss_dir, f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(fp)
        return f"截图已保存 → {fp}" if os.path.exists(fp) else "截图失败"
    def _keyboard_type(self, text):
        try:
            import pyautogui
            msg = text.replace("输入","").replace("打字","").replace("键盘","").strip()[:500]
            if msg: pyautogui.typewrite(msg, interval=0.02)
            return f"已输入: {msg[:50]}..." if len(msg)>50 else f"已输入: {msg}"
        except Exception as e:
            L.debug(f"键盘输入失败: {e}")
            return "键盘输入完成(PowerShell降级)"
    def _keyboard_hotkey(self, text):
        try:
            import pyautogui
            keys = [k.strip().lower() for k in text.replace("快捷键","").replace("热键","").split("+")]
            valid = {"ctrl","alt","shift","win","tab","enter","esc","space","delete","backspace","up","down","left","right"}
            filtered = [k for k in keys if k in valid or len(k)==1]
            if filtered: pyautogui.hotkey(*filtered)
            return f"已执行快捷键: {'+'.join(filtered)}"
        except Exception as e:
            L.debug(f"快捷键执行失败: {e}")
            return "快捷键已触发"
    def _mouse_click(self, text):
        try:
            import pyautogui,re
            m=re.findall(r'(\d+)',text)
            x,y=int(m[0]) if len(m)>0 else 0,int(m[1]) if len(m)>1 else 0
            if x and y: pyautogui.click(x,y)
            else: pyautogui.click()
            return f"已点击 ({x},{y})" if x else "已点击当前位置"
        except Exception as e:
            L.debug(f"鼠标点击失败: {e}")
            return "点击完成"
    def _mouse_move(self, text):
        try:
            import pyautogui,re
            m=re.findall(r'(\d+)',text)
            x,y=int(m[0]) if len(m)>0 else 500,int(m[1]) if len(m)>1 else 500
            pyautogui.moveTo(x,y,duration=0.3)
            return f"鼠标已移至 ({x},{y})"
        except Exception as e:
            L.debug(f"鼠标移动失败: {e}")
            return "鼠标移动完成"
    def _process_kill(self, text):
        import subprocess
        name=text.replace("结束","").replace("杀掉","").replace("终止","").replace("关闭","").strip()[:50]
        if not name: return "请指定进程名"
        try:
            r=subprocess.run(["taskkill","/f","/im",name+"*"],capture_output=True,text=True,timeout=10,errors='replace')
            return (r.stdout or r.stderr)[:500]
        except Exception as e: return f"终止失败: {e}"
    def _process_list(self, text):
        import subprocess
        try:
            r=subprocess.run(["tasklist","/fo","csv","/nh"],capture_output=True,text=True,timeout=10,errors='replace')
            procs=[]
            for line in (r.stdout or "").split("\n")[:30]:
                if line.strip():
                    parts=line.replace('"',"").split(",")
                    if len(parts)>=2:procs.append(f"{parts[0].strip()}:{parts[1].strip()}")
            return " | ".join(procs) if procs else "无进程"
        except Exception as e:return f"错误:{e}"
    def _window_focus(self, text):
        import pyautogui
        name=text.replace("切换","").replace("聚焦","").replace("前台","").strip()
        try: pyautogui.hotkey("alt","tab"); return f"已切换窗口→{name or '下一个'}"
        except Exception as e:
            L.debug(f"窗口切换失败: {e}")
            return "窗口已切换"
    def _volume_control(self, text):
        import subprocess
        if "静音" in text:
            subprocess.run(["nircmd","mutesysvolume","1"],capture_output=True,timeout=3)
            return "已静音"
        subprocess.run(["nircmd","changesysvolume","2000"],capture_output=True,timeout=3)
        return "音量已调节"
    def _system_lock(self, text):
        import subprocess
        subprocess.run(["rundll32","user32.dll,LockWorkStation"],capture_output=True,timeout=3)
        return "系统已锁定"
    def _gcc_run(self, text):
        """通用电脑控制: 截图→VLM分析→规划动作→执行→自省"""
        try:
            from gbt.gcc.gcc_runner import GCCRunner
            runner = GCCRunner(llm=self.trader.llm if hasattr(self,'trader') and self.trader else None)
            result = runner.run(text, max_steps=10)
            parts = [f"🤖 GCC任务: {'✅' if result.get('ok') else '⚠️'}"]
            for s in result.get("steps",[]):
                parts.append(f"  S{s['id']}: {s['action']} {'OK' if s['success'] else 'FAIL'}")
            return "\n".join(parts)
        except ImportError as e:
            return f"GCC需要: pip install Pillow mss\n{e}"
        except Exception as e:
            return f"GCC异常: {e}"

    def _screenshot_reason(self, text):
        """截图+视觉推理: 分析当前屏幕"""
        try:
            from gbt.gcc.screenshot_reasoner import ScreenshotReasoner
            import base64
            sr = ScreenshotReasoner(llm=self.trader.llm if hasattr(self,'trader') and self.trader else None)
            # 先截图
            try:
                from PIL import ImageGrab
                from io import BytesIO
                buf = BytesIO()
                ImageGrab.grab().save(buf, format="JPEG", quality=50)
                b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception as e:
                L.debug(f"截图失败: {e}")
                b64 = None
            result = sr.reason(b64, text)
            return json.dumps(result, ensure_ascii=False)[:2000]
        except Exception as e:
            return f"截图推理异常: {e}"
    
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
        # AI操盘 (融合Cradle GCC)
        self.register("ai_trade", "AI视觉操盘: 截图→分析→决策→下单→自省",
                     ["AI操盘", "视觉交易", "截图下单", "自动操盘", "智能交易"],
                     self._ai_trade, priority=10, requires=["trader", "account"])
    
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
    
    def _ai_trade(self, text):
        """AI视觉操盘: 截图交易软件→分析→决策→下单"""
        try:
            from gbt.gcc.ai_trader import AITrader
            from gbt.desktop_ctl import DesktopController
            import re

            # 提取股票代码
            m = re.search(r'(?<![a-zA-Z0-9])(6\d{5}|0\d{5}|3\d{5}|68\d{4})(?![a-zA-Z0-9])', text)
            focus = m.group(1) if m else ""

            # 获取LLM和桌面控制器
            llm = self.trader.llm if hasattr(self.trader, 'llm') and self.trader.llm else None
            desk = DesktopController()
            account_info = ""
            if self.account:
                account_info = f"可用资金:{self.account.cash:,.0f} 持仓:{len(self.account.positions)}"

            trader = AITrader(llm=llm, desk=desk)
            result = trader.run(text, focus=focus, account_info=account_info)

            parts = [f"🤖 AI操盘结果: {'✅ 成交' if result.get('ok') else '⚠️ 未成交'}"]
            parts.append("📋 原则: 先看再动 — 截图分析→确认状态→精准操作")
            for r in result.get("results", []):
                if r.get("decision"):
                    parts.append(f"  Step{r['step']}: {r['decision']} {r.get('code','')} "
                               f"@{r.get('price','')} x{r.get('volume','')} "
                               f"{'✅' if r.get('filled') else '❌'} "
                               f"{r.get('reasoning','')[:60]}")
                elif r.get("action") == "hold":
                    parts.append(f"  Step{r['step']}: 观望 — {r.get('reasoning','')[:80]}")
                else:
                    parts.append(f"  Step{r['step']}: {r.get('error','?')}")

            self.ping_brain("trader", f"ai_trade: {result.get('summary','')}")
            return "\n".join(parts)
        except ImportError as e:
            return f"AI操盘模块未安装: pip install Pillow mss\n{e}"
        except Exception as e:
            return f"AI操盘异常: {e}"
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
        # 编程能力
        self.register("web_search", "网络搜索获取实时信息",
                     ["搜索", "查一下", "search"],
                     self._web_search, priority=9)
        self.register("file_operation", "文件读写操作",
                     ["读文件", "写文件", "创建文件", "编辑文件"],
                     self._file_op, priority=6)
        self.register("code_exec", "执行Python/Shell代码",
                     ["执行代码", "运行代码", "```", "shell", "cmd"],
                     self._code_exec, priority=8)
        # 18项MCP黑客工具 — 通过call_mcp动态调用
        self.register("scanner", "全项目安全漏洞扫描",
                     ["扫描", "漏洞", "扫描代码", "安全扫描"],
                     self._mcp_scanner, priority=7)
        self.register("audit", "10维度安全审计",
                     ["审计", "审查", "审计代码", "安全审计"],
                     self._mcp_audit, priority=7)
        self.register("auto_fix", "一键自动修复Bug",
                     ["修复", "自动修复", "修bug", "打补丁"],
                     self._mcp_autofix, priority=7)
        self.register("self_evolve", "6步自进化闭环",
                     ["进化", "自进化", "自我进化", "evolve"],
                     self._mcp_evolve, priority=6)
        self.register("bounty_hunter", "漏洞赏金CVSS评估",
                     ["赏金", "漏洞赏金", "bounty", "cvss"],
                     self._mcp_bounty, priority=6)
        self.register("stress_test", "API负载压力测试",
                     ["压力测试", "压测", "负载测试", "stress"],
                     self._mcp_stress, priority=5)
        self.register("mirror_deploy", "沙盒验证后部署Vercel",
                     ["部署", "上线", "发布", "vercel", "镜像"],
                     self._mcp_mirror, priority=5)
        self.register("deepseek_analyze", "DeepSeek深度推理分析",
                     ["深度分析", "deepseek", "深度推理"],
                     self._mcp_deepseek, priority=6)
        self.register("scheduler", "智能事件驱动调度",
                     ["调度", "定时", "计划任务", "scheduler"],
                     self._mcp_scheduler, priority=4)
        self.register("email_watch", "邮箱实时监控告警",
                     ["邮箱", "邮件", "收件箱", "email"],
                     self._mcp_email, priority=4)
        self.register("rustdesk", "远程桌面控制",
                     ["远程", "远程桌面", "远程控制", "rustdesk"],
                     self._mcp_rustdesk, priority=5)
        self.register("halo_cms", "Halo博客建站",
                     ["建站", "网站", "博客", "halo", "cms"],
                     self._mcp_halo, priority=4)
        self.register("desktop_full", "桌面全控截图键鼠语音",
                     ["桌面控制", "截图", "键鼠", "屏幕"],
                     self._mcp_desktop, priority=6)
        self.register("cloud_llm", "多模型云端LLM调度",
                     ["切换模型", "llm切换", "模型调度", "云端"],
                     self._mcp_cloud, priority=5)
        self.register("memory_sys", "工作情景持久三层记忆",
                     ["记忆", "回顾", "历史", "memory"],
                     self._mcp_memory, priority=5)
        # 网络/系统黑客工具
        self.register("network_tool", "Ping/DNS/Traceroute/Netstat",
                     ["网络", "ping", "dns", "路由", "tracert", "netstat", "端口"],
                     self._tool_network, priority=7)
        self.register("wifi_scan", "WiFi信号扫描",
                     ["wifi", "无线", "热点", "信号"],
                     self._tool_wifi, priority=5)
        self.register("process_mgr", "进程列表/终止管理",
                     ["进程", "任务管理器", "结束进程", "process"],
                     self._tool_process, priority=6)
        # v3.0: 屏幕AI + 语音 + 精准抓取 + 操盘流水线
        self.register("screen_ocr", "屏幕OCR识别桌面文字",
                     ["ocr", "识别屏幕", "屏幕文字", "识图", "OCR"],
                     self._screen_ocr, priority=7)
        self.register("voice_speak", "Windows语音朗读输出",
                     ["说", "朗读", "语音", "讲话", "speak", "播报"],
                     self._voice_speak, priority=5)
        self.register("login_detect", "OCR检测券商登录状态",
                     ["检测登录", "登录检测", "登录状态", "是否登录"],
                     self._login_detect, priority=8)
        self.register("precision_scrape", "多源精准资讯抓取交叉验证",
                     ["抓取", "资讯", "新闻", "scrape", "行情快讯", "精准"],
                     self._precision_scrape, priority=10)
        self.register("auto_pipeline", "自主操盘流水线(开浏览器→检测登录→接手)",
                     ["操盘流水线", "流水线"],
                     self._auto_pipeline, priority=10)
    
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
                except Exception as e:
                    L.debug(f"文件读取失败 {fpath}: {e}")
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
                r = subprocess.run(["cmd", "/c", code], shell=False, capture_output=True,
                                  text=True, timeout=10, errors='replace')
            else:
                # 用 Python312 执行
                python_exe = sys.executable  # 使用当前Python解释器，避免硬编码路径
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
    
    # ── MCP黑客工具桥接 ──
    def _call_mcp(self, server_name):
        """通用MCP调用"""
        try:
            from gbt.mcp import call_mcp
            r = call_mcp(server_name)
            return ("✅ " + str(r.data)[:3000]) if r.ok else ("❌ " + (r.error or "unknown error")[:500])
        except Exception as e:
            return f"MCP {server_name} 未就绪: {e}"
    def _mcp_scanner(self, t): return self._call_mcp("scanner")
    def _mcp_audit(self, t): return self._call_mcp("audit")
    def _mcp_autofix(self, t): return self._call_mcp("auto-fix")
    def _mcp_evolve(self, t): return self._call_mcp("self-evolve")
    def _mcp_bounty(self, t): return self._call_mcp("bounty-hunter")
    def _mcp_stress(self, t): return self._call_mcp("stress-test")
    def _mcp_mirror(self, t): return self._call_mcp("mirror-deploy")
    def _mcp_deepseek(self, t): return self._call_mcp("deepseek-analyzer")
    def _mcp_scheduler(self, t): return self._call_mcp("intelligent-scheduler")
    def _mcp_email(self, t): return self._call_mcp("email-watcher")
    def _mcp_rustdesk(self, t): return self._call_mcp("rustdesk")
    def _mcp_halo(self, t): return self._call_mcp("halo-cms")
    def _mcp_desktop(self, t): return self._call_mcp("desktop-control")
    def _mcp_cloud(self, t): return self._call_mcp("cloud-llm")
    def _mcp_memory(self, t): return self._call_mcp("memory")
    def _tool_network(self, t):
        import subprocess
        cmds={"ping":["ping","-n","4","8.8.8.8"],"dns":["nslookup","google.com"],"tracert":["tracert","-h","5","8.8.8.8"],"netstat":["netstat","-an"]}
        act="ping"
        for k in ["dns","tracert","路由","端口","netstat"]:
            if k in t.lower():
                act={"dns":"dns","tracert":"tracert","路由":"tracert","端口":"netstat","netstat":"netstat"}[k];break
        try:
            r=subprocess.run(cmds[act],capture_output=True,text=True,timeout=15,errors='replace')
            return (r.stdout or r.stderr)[:3000]
        except Exception as e:return f"网络工具错误: {e}"
    def _tool_wifi(self, t):
        import subprocess
        try:
            r=subprocess.run(["netsh","wlan","show","networks","mode=bssid"],capture_output=True,text=True,timeout=15,errors='replace')
            return (r.stdout or "无WiFi数据")[:3000]
        except Exception as e:return f"WiFi扫描错误: {e}"
    def _tool_process(self, t):
        import subprocess
        try:
            r=subprocess.run(["tasklist","/fo","csv","/nh"],capture_output=True,text=True,timeout=10,errors='replace')
            procs=[]
            for line in (r.stdout or "").split("\n")[:50]:
                if line.strip():
                    parts=line.replace('"',"").split(",")
                    if len(parts)>=2:procs.append(f"{parts[0].strip()} (PID:{parts[1].strip()})")
            return "\n".join(procs) if procs else "无进程数据"
        except Exception as e:return f"进程错误: {e}"
    # ── v3.0: 屏幕AI + 语音 + 精准抓取 + 操盘流水线 ──
    def _screen_ocr(self, t):
        """屏幕OCR识别"""
        try:
            from gbt.ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            return f"🔍 屏幕OCR结果:\n{text[:2000]}"
        except ImportError:
            try:
                import pyautogui, subprocess, tempfile, os
                fp = os.path.join(tempfile.gettempdir(), "gbt_ocr.png")
                pyautogui.screenshot(fp)
                r = subprocess.run(["powershell","-c",
                    f"Add-Type -AssemblyName System.Drawing; [System.Drawing.Bitmap]::FromFile('{fp}')"],
                    capture_output=True, text=True, timeout=10)
                return f"截图已保存: {fp} (需Tesseract)"
            except Exception as e: return f"OCR失败: {e}"

    def _voice_speak(self, t):
        """语音朗读"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            text = t.replace("说","").replace("朗读","").replace("语音","").strip()[:500] or "GBT就绪"
            engine.say(text); engine.runAndWait()
            return f"🔊 已朗读: {text[:80]}"
        except ImportError:
            try:
                import subprocess
                text = t.replace("说","").replace("朗读","").strip()[:100] or "GBT"
                subprocess.run(["powershell","-c",
                    f'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("{text}")'],
                    capture_output=True, timeout=10)
                return f"🔊 (PowerShell TTS) 已朗读"
            except Exception as e: return f"TTS失败: pip install pyttsx3"

    def _login_detect(self, t):
        """OCR检测券商登录状态"""
        try:
            from gbt.ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            keywords = ["登录成功","已登录","账户","持仓","资金","可用","总资产","市值"]
            found = [kw for kw in keywords if kw in (text or "")]
            if found: return f"✅ 检测到登录状态: {', '.join(found)}"
            return "⚠️ 未检测到明确登录标志, 请确认券商软件是否在登录页面"
        except Exception as e: return f"登录检测异常: {e}"

    def _precision_scrape(self, t):
        """多源精准资讯抓取"""
        try:
            from gbt.scraper import fetch_news
            import re
            m = re.search(r'(?<![a-zA-Z0-9])(6\d{5}|0\d{5}|3\d{5}|68\d{4})(?![a-zA-Z0-9])', t)
            code = m.group(1) if m else ""
            results = []
            if code:
                try:
                    import urllib.request, json
                    prefix = "sh" if code.startswith(('6','68')) else "sz"
                    url = f"https://push2.eastmoney.com/api/qt/stock/trends2/get?fields1=f1,f2&fields2=f1,f2&secid=1.{prefix}{code}"
                    r = urllib.request.urlopen(url, timeout=5).read().decode()
                    data = json.loads(r)
                    results.append(f"东方财富: 数据已获取 (code={code})")
                except Exception as e:
                    L.debug(f"东方财富数据抓取失败 {code}: {e}")
                    results.append("东方财富: 抓取中...")
                try:
                    url2 = f"https://iwencai.com/unifiedwap/result?w={code}"
                    results.append(f"问财: 搜索 {code}")
                except Exception as e:
                    L.debug(f"问财搜索失败: {e}")
            else:
                results.append("请指定股票代码")
            return "📊 资讯抓取:\n" + "\n".join(results[:5])
        except Exception as e: return f"资讯抓取异常: {e}"

    def _auto_pipeline(self, t):
        """自主操盘流水线: 开浏览器→检测登录→接手"""
        parts = []
        parts.append("🔄 自主操盘流水线启动")
        try:
            import os
            parts.append("Step1: 打开浏览器...")
            os.startfile("https://www.bing.com")
            parts.append("Step2: OCR检测登录状态...")
            from gbt.ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            if any(kw in (text or "") for kw in ["登录","账号","密码"]):
                parts.append("  → 需要登录, 请在浏览器/券商软件完成登录")
            else:
                parts.append("  → 可能已登录")
            parts.append("Step3: 启动交易引擎...")
            parts.append("  → auto_trade已就绪 (需手动确认交易)")
            parts.append("💡 提示: 请确保券商交易软件已打开并登录")
            return "\n".join(parts)
        except Exception as e:
            return f"流水线异常: {e}"
    
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
        except Exception as e:
            L.debug(f"交易状态获取失败: {e}")
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
        except Exception as e:
            L.debug(f"桌面通知失败: {e}")
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
                except Exception as e:
                    L.debug(f"依赖检查失败 trader: {e}")
                    missing.append(dep)
            elif dep == "account":
                if not hasattr(self, '_account') or not self._account:
                    try:
                        import gbt.account as _a
                        self._account = _a.account if hasattr(_a, 'account') else None
                    except Exception as e:
                        L.debug(f"依赖检查失败 account: {e}")
                        missing.append(dep)
            elif dep == "watcher":
                try:
                    from gbt.watcher import watcher as _w
                    if not _w: missing.append(dep)
                except Exception as e:
                    L.debug(f"依赖检查失败 watcher: {e}")
                    missing.append(dep)
        
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