"""
watcher_agent.py — 守夜人 AI Agent v1.0
独立第二Agent，不参与项目改动，只监控+纠偏

职责：
 1. 心跳捕捉日志 → 发现异常触发主Agent自主修复
 2. 实时监控连接链路 → 断连触发主Agent重新连接打补丁
 3. 监听主Agent大模型 → 检测幻觉立即纠正
 4. 扫描项目结构 → 发现主Agent跑偏立刻唤醒纠正
 5. 同步上下文和记忆 → 与主Agent保持一致性

红线：只读模式，绝不修改项目文件、不执行交易、不触碰代码
"""
import os, sys, json, time, re, hashlib, threading, traceback
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import logging
L = logging.getLogger("GBT.WatcherAgent")


# ═══════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════

@dataclass
class WatchFinding:
    """守夜人发现"""
    timestamp: str
    category: str          # hallucination / connection / anomaly / drift / structural
    severity: str          # info / warn / critical
    source: str            # 来源模块
    message: str           # 描述
    suggestion: str        # 建议主Agent操作
    context: dict = field(default_factory=dict)

@dataclass 
class MemorySnapshot:
    """记忆快照"""
    path: str
    hash: str
    size: int
    last_modified: str


# ═══════════════════════════════════════════════════════
# 守夜人 Agent 核心
# ═══════════════════════════════════════════════════════

class WatcherAgent:
    """守夜人 AI Agent — 独立的第二Agent"""
    
    def __init__(self, project_root: str, main_brain=None):
        self.project_root = project_root
        self.main_brain = main_brain  # 主Agent大脑引用（用于ping）
        self.running = False
        self._lock = threading.Lock()
        
        # 状态
        self.findings: list[WatchFinding] = []
        self.memory_snapshots: dict[str, MemorySnapshot] = {}
        self.last_full_scan: Optional[str] = None
        self.heartbeat_count = 0
        self.hallucination_count = 0
        self.connection_alerts = 0
        self.drift_alerts = 0
        
        # 监控配置
        self.ROOT = project_root
        self.LOG_DIR = os.path.join(project_root, 'logs')
        self.MEMORY_DIR = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'memory')
        self.HEARTBEAT_PATH = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'HEARTBEAT.md')
        self.MEMORY_PATH = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'MEMORY.md')
        
        # 关键文件监控清单
        self.WATCH_FILES = [
            os.path.join(project_root, 'gbt', 'brain.py'),
            os.path.join(project_root, 'gbt', 'trader.py'),
            os.path.join(project_root, 'gbt', 'router.py'),
            os.path.join(project_root, 'gbt', 'watcher.py'),
            os.path.join(project_root, 'gbt', 'capabilities.py'),
            os.path.join(project_root, 'gbt', 'protocol.py'),
            os.path.join(project_root, 'gbt', 'account.py'),
            os.path.join(project_root, 'gbt', 'risk_ctrl.py'),
            os.path.join(project_root, 'gbt', 'llm.py'),
            os.path.join(project_root, 'desktop', 'app.py'),
        ]
        
        # 幻觉检测模式
        self.HALLUCINATION_PATTERNS = [
            (r'(?:价格|股价|收盘价).*?(\d+\.\d+).*?(?:元|块)', '疑似编造价格数据'),
            (r'(?:成交|买入|卖出).*?(\d+).*?(?:股|手).*?(?:成功|完成)', '疑似编造交易记录'),
            (r'(?:报告|文件|数据).*?(?:显示|表明|指出).*?(?:但|然而|不过).*?(?:不|未|无)', '疑似引用不存在的文件'),
            (r'(?:API|接口|端口).*?(?:返回|响应|连接).*?(?:成功|正常|ok)', '疑似编造接口状态'),
            (r'我.*?(?:记得|之前|上次).*?(?:说过|做过|修复)', '疑似伪造历史对话'),
            (r'(?:已|已经).*?(?:修复|解决|完成|实现)', '需验证实际修复状态'),
            (r'(?:所有|全部|每个).*?(?:正常|通过|ok|pass)', '确定性断言需验证'),
        ]
        
        L.info("🦉 守夜人Agent v1.0 初始化完成")
    
    # ═══════════════════════════════════════════════════════
    # 1. 记忆同步
    # ═══════════════════════════════════════════════════════
    
    def sync_memory(self):
        """同步记忆快照 — 与主Agent保持上下文一致"""
        snapshots = {}
        for path in [self.MEMORY_PATH, self.MEMORY_DIR]:
            if not path:
                continue
            if os.path.isfile(path):
                snapshots[path] = self._snapshot_file(path)
            elif os.path.isdir(path):
                for f in os.listdir(path):
                    fpath = os.path.join(path, f)
                    if f.endswith('.md') or f.endswith('.json'):
                        snapshots[fpath] = self._snapshot_file(fpath)
        
        changed = []
        for path, snap in snapshots.items():
            old = self.memory_snapshots.get(path)
            if old and old.hash != snap.hash:
                changed.append(path)
            elif not old:
                changed.append(path)  # 新文件
        
        self.memory_snapshots = snapshots
        if changed:
            L.info(f"🧠 记忆同步: {len(snapshots)}文件, {len(changed)}变化")
        return changed
    
    def _snapshot_file(self, path: str) -> MemorySnapshot:
        try:
            with open(path, 'rb') as f:
                content = f.read()
            return MemorySnapshot(
                path=path,
                hash=hashlib.md5(content).hexdigest(),
                size=len(content),
                last_modified=datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
            )
        except:
            return MemorySnapshot(path=path, hash='error', size=0, last_modified='?')
    
    # ═══════════════════════════════════════════════════════
    # 2. 幻觉检测
    # ═══════════════════════════════════════════════════════
    
    def detect_hallucination(self, text: str, source: str = "unknown") -> list[WatchFinding]:
        """检测大模型输出中的幻觉"""
        findings = []
        for pattern, concern in self.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                finding = WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="hallucination",
                    severity="warn",
                    source=source,
                    message=f"{concern}: {matches[0][:60] if isinstance(matches[0], tuple) else str(matches[0])[:60]}",
                    suggestion="请主Agent核实并纠正，避免传播不实信息",
                    context={"pattern": pattern, "matches": len(matches)}
                )
                findings.append(finding)
                self.hallucination_count += 1
        
        if findings:
            self.findings.extend(findings)
            L.warning(f"🔍 幻觉检测: {len(findings)}处可疑 → {source}")
        
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 3. 日志异常检测
    # ═══════════════════════════════════════════════════════
    
    def scan_logs(self) -> list[WatchFinding]:
        """扫描日志文件发现异常"""
        findings = []
        if not os.path.exists(self.LOG_DIR):
            return findings
        
        log_files = [f for f in os.listdir(self.LOG_DIR) if f.endswith('.log')]
        
        for log_file in log_files:
            fpath = os.path.join(self.LOG_DIR, log_file)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                # 只看最近500行
                recent = lines[-500:] if len(lines) > 500 else lines
                
                error_count = sum(1 for l in recent if 'ERROR' in l or 'CRITICAL' in l)
                warn_count = sum(1 for l in recent if 'WARNING' in l)
                traceback_count = sum(1 for l in recent if 'Traceback' in l)
                
                if error_count > 0:
                    findings.append(WatchFinding(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        category="anomaly",
                        severity="critical" if error_count > 5 else "warn",
                        source=log_file,
                        message=f"日志异常: {error_count}错误/{warn_count}警告/{traceback_count}异常",
                        suggestion="请主Agent检查错误日志，执行自主修复",
                        context={"errors": error_count, "warns": warn_count, "tracebacks": traceback_count}
                    ))
                
                # 检测大模型幻觉在日志中
                for line in recent:
                    for keyword in ['编造', '假数据', '不存在的', '伪造', '幻觉']:
                        if keyword in line:
                            findings.append(WatchFinding(
                                timestamp=datetime.now().strftime("%H:%M:%S"),
                                category="hallucination",
                                severity="critical",
                                source=log_file,
                                message=f"日志中发现幻觉标记: {line.strip()[:80]}",
                                suggestion="主Agent应立即停止当前操作并纠正"
                            ))
                            break
                            
            except Exception as e:
                L.warning(f"日志扫描异常 {log_file}: {e}")
        
        if findings:
            self.findings.extend(findings)
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 4. 连接链路监控
    # ═══════════════════════════════════════════════════════
    
    def check_connections(self) -> list[WatchFinding]:
        """监控所有连接链路"""
        findings = []
        
        # 4.1 GBT API
        try:
            import urllib.request
            r = urllib.request.urlopen('http://localhost:8877/api/status', timeout=5)
            if r.getcode() != 200:
                raise Exception(f"HTTP {r.getcode()}")
        except Exception as e:
            findings.append(WatchFinding(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                category="connection",
                severity="critical",
                source="GBT API (8877)",
                message=f"GBT API不可达: {str(e)[:60]}",
                suggestion="主Agent检查GBT进程，必要时重启"
            ))
            self.connection_alerts += 1
        
        # 4.2 MCP服务器
        try:
            from gbt.mcp import get_mcp, call_mcp
            mcp = get_mcp()
            down = []
            for name in mcp._s:
                try:
                    r = call_mcp(name, "status", timeout=2)
                    if not r.ok:
                        down.append(name)
                except:
                    down.append(name)
            
            if down:
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="connection",
                    severity="critical" if len(down) > 3 else "warn",
                    source="MCP Servers",
                    message=f"{len(down)}/{len(mcp._s)} MCP服务断连: {'; '.join(down[:3])}",
                    suggestion="主Agent执行MCP重连修复打补丁",
                    context={"down": down, "total": len(mcp._s)}
                ))
                self.connection_alerts += 1
        except Exception as e:
            findings.append(WatchFinding(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                category="connection",
                severity="critical",
                source="MCP Module",
                message=f"MCP模块不可用: {str(e)[:60]}",
                suggestion="主Agent检查MCP模块导入和配置"
            ))
        
        # 4.3 新浪行情API
        try:
            import urllib.request
            r = urllib.request.urlopen('https://hq.sinajs.cn/list=sh000001', timeout=5)
            if 'var hq_str' not in r.read().decode('gbk', errors='replace'):
                raise Exception("响应格式异常")
        except Exception as e:
            findings.append(WatchFinding(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                category="connection",
                severity="critical",
                source="Sina HQ API",
                message=f"行情源不可达: {str(e)[:60]}",
                suggestion="主Agent检查网络连接，切换备用行情源"
            ))
            self.connection_alerts += 1
        
        # 4.4 DeepSeek LLM API
        try:
            import urllib.request, os
            api_key = os.environ.get('DEEPSEEK_API_KEY', '')
            if not api_key:
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="connection",
                    severity="critical",
                    source="LLM API Key",
                    message="DEEPSEEK_API_KEY未设置",
                    suggestion="主Agent检查环境变量配置"
                ))
        except Exception as e:
            pass
        
        if findings:
            self.findings.extend(findings)
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 5. 项目结构扫描 — 检测主Agent跑偏
    # ═══════════════════════════════════════════════════════
    
    def scan_project_structure(self) -> list[WatchFinding]:
        """扫描项目结构，检测主Agent是否跑偏"""
        findings = []
        
        # 5.1 关键文件完整性
        for fpath in self.WATCH_FILES:
            if not os.path.exists(fpath):
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="structural",
                    severity="critical",
                    source="project",
                    message=f"关键文件缺失: {os.path.relpath(fpath, self.ROOT)}",
                    suggestion="主Agent检查文件是否被误删，从git恢复"
                ))
        
        # 5.2 Git状态检查
        try:
            import subprocess
            r = subprocess.run(['git', 'status', '--porcelain'],
                             cwd=self.ROOT, capture_output=True, text=True,
                             errors='replace', timeout=10)
            changes = [l for l in r.stdout.strip().split('\n') if l.strip()]
            
            # 分类变更
            modified = [l for l in changes if l.startswith(' M') or l.startswith('M ')]
            untracked = [l for l in changes if l.startswith('??')]
            deleted = [l for l in changes if l.startswith(' D') or l.startswith('D ')]
            
            if deleted:
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="drift",
                    severity="warn",
                    source="git",
                    message=f"检测到{len(deleted)}个文件被删除",
                    suggestion="主Agent确认是否为预期操作，非预期则git restore恢复",
                    context={"deleted": [l[3:] for l in deleted[:5]]}
                ))
                self.drift_alerts += 1
            
            # 检测意外的大量变更（可能跑偏）
            if len(modified) > 10:
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="drift",
                    severity="warn",
                    source="git",
                    message=f"大量文件变更({len(modified)}个)，主Agent可能跑偏",
                    suggestion="主Agent回顾近期操作，确认变更合理性",
                    context={"modified": [l[3:] for l in modified[:5]]}
                ))
                self.drift_alerts += 1
                
        except Exception as e:
            L.warning(f"Git扫描异常: {e}")
        
        # 5.3 Python语法检查（检测主Agent是否写了坏代码）
        import py_compile
        for fpath in self.WATCH_FILES:
            if not fpath.endswith('.py'):
                continue
            try:
                py_compile.compile(fpath, doraise=True)
            except py_compile.PyCompileError as e:
                findings.append(WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="drift",
                    severity="critical",
                    source=os.path.basename(fpath),
                    message=f"Python语法错误: {str(e)[:80]}",
                    suggestion="主Agent立即修复该文件的语法错误"
                ))
                self.drift_alerts += 1
        
        if findings:
            self.findings.extend(findings)
        self.last_full_scan = datetime.now().strftime("%H:%M:%S")
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 6. 心跳主循环
    # ═══════════════════════════════════════════════════════
    
    def heartbeat(self):
        """单次心跳 — 执行所有监控检查"""
        self.heartbeat_count += 1
        now = datetime.now().strftime("%H:%M:%S")
        all_findings = []
        
        # 1. 同步记忆
        memory_changes = self.sync_memory()
        if memory_changes:
            L.info(f"📝 记忆变更: {len(memory_changes)}文件")
        
        # 2. 扫描日志
        log_findings = self.scan_logs()
        all_findings.extend(log_findings)
        
        # 3. 检查连接
        conn_findings = self.check_connections()
        all_findings.extend(conn_findings)
        
        # 4. 每10次心跳做一次完整结构扫描
        if self.heartbeat_count % 10 == 0:
            struct_findings = self.scan_project_structure()
            all_findings.extend(struct_findings)
        
        # 5. 有发现 → 唤醒主Agent
        if all_findings and self.main_brain:
            self._wake_main_agent(all_findings)
        
        # 清理旧发现（保留最近100条）
        if len(self.findings) > 100:
            self.findings = self.findings[-100:]
        
        return {
            "heartbeat": self.heartbeat_count,
            "time": now,
            "findings": len(all_findings),
            "total_findings": len(self.findings),
            "stats": {
                "hallucination": self.hallucination_count,
                "connection_alerts": self.connection_alerts,
                "drift_alerts": self.drift_alerts,
            }
        }
    
    def _wake_main_agent(self, findings: list[WatchFinding]):
        """唤醒主Agent — 通过brain.ping发送发现"""
        if not self.main_brain:
            return
        
        try:
            criticals = [f for f in findings if f.severity == "critical"]
            warns = [f for f in findings if f.severity == "warn"]
            
            # 构建摘要消息
            summary_parts = []
            if criticals:
                summary_parts.append(f"🔴 {len(criticals)}个严重问题")
                for c in criticals[:3]:
                    summary_parts.append(f"  [{c.category}] {c.message[:50]}")
            if warns:
                summary_parts.append(f"🟡 {len(warns)}个警告")
            
            summary = "; ".join(summary_parts[:5])  # 最多5条
            
            # Ping主Agent大脑
            if self.main_brain.running:
                self.main_brain.ping("watcher_agent", summary[:200])
                L.info(f"🔔 唤醒主Agent: {summary[:100]}")
                
                # 保存发现到watcher告警（如果可用）
                try:
                    from gbt.watcher import watcher as _w
                    for f in criticals[:3]:
                        _w._add_alert("watcher_agent", "critical" if f.severity == "critical" else "warn",
                                     f.message[:100], f.suggestion[:100])
                except:
                    pass
                    
        except Exception as e:
            L.error(f"唤醒主Agent失败: {e}")
    
    # ═══════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════
    
    def start(self, main_brain=None):
        """启动守夜人Agent"""
        if main_brain:
            self.main_brain = main_brain
        
        self.running = True
        L.info(f"🦉 守夜人Agent已启动 — 监控中")
        
        # 首次快速扫描
        self.sync_memory()
        self.scan_project_structure()
        
        return {"ok": True, "version": "v1.0", "mode": "readonly"}
    
    def stop(self):
        """停止守夜人Agent"""
        self.running = False
        L.info("🦉 守夜人Agent已停止")
    
    def get_status(self):
        """获取状态"""
        return {
            "running": self.running,
            "version": "v1.0",
            "heartbeat_count": self.heartbeat_count,
            "memory_snapshots": len(self.memory_snapshots),
            "findings": len(self.findings),
            "stats": {
                "hallucination": self.hallucination_count,
                "connection_alerts": self.connection_alerts,
                "drift_alerts": self.drift_alerts,
            },
            "last_full_scan": self.last_full_scan,
            "recent_findings": [
                {
                    "time": f.timestamp,
                    "category": f.category,
                    "severity": f.severity,
                    "message": f.message[:80],
                    "suggestion": f.suggestion[:80],
                }
                for f in self.findings[-10:]
            ],
            "mode": "readonly — 不参与项目改动"
        }


# ═══════════════════════════════════════════════════════
# 自动发现LLM响应并检测幻觉的钩子
# ═══════════════════════════════════════════════════════

class LLMResponseMonitor:
    """拦截大模型响应，检测幻觉"""
    
    def __init__(self, watcher_agent: WatcherAgent):
        self.agent = watcher_agent
        self.enabled = True
    
    def audit(self, response_text: str, source: str = "llm") -> Optional[list[WatchFinding]]:
        """审计大模型响应"""
        if not self.enabled or not response_text:
            return None
        return self.agent.detect_hallucination(response_text, source)
    
    def check_api_response(self, response_json: dict) -> Optional[list[WatchFinding]]:
        """检查API响应质量"""
        findings = []
        
        # 空响应检测
        conclusion = response_json.get('conclusion', '')
        if not conclusion or len(conclusion) < 10:
            findings.append(WatchFinding(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                category="hallucination",
                severity="warn",
                source="API",
                message="大模型返回空响应或过短响应",
                suggestion="主Agent检查LLM连接，必要时重试"
            ))
        
        # 协议错误检测
        protocol = response_json.get('protocol', {})
        if isinstance(protocol, dict) and not protocol.get('ok', True):
            findings.append(WatchFinding(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                category="anomaly",
                severity="warn",
                source="Protocol",
                message=f"协议执行失败: {protocol.get('error_level','?')}",
                suggestion="主Agent检查协议链路，定位失败阶段"
            ))
        
        # 幻觉内容检测
        if conclusion:
            h = self.agent.detect_hallucination(conclusion, source)
            if h:
                findings.extend(h)
        
        return findings if findings else None


# ═══════════════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════════════

_watcher_agent_instance: Optional[WatcherAgent] = None
_llm_monitor_instance: Optional[LLMResponseMonitor] = None


def get_watcher_agent(project_root: str = None, main_brain=None) -> WatcherAgent:
    """获取守夜人Agent单例"""
    global _watcher_agent_instance
    if _watcher_agent_instance is None:
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(__file__))
        _watcher_agent_instance = WatcherAgent(project_root, main_brain)
    elif main_brain and _watcher_agent_instance.main_brain is None:
        _watcher_agent_instance.main_brain = main_brain
    return _watcher_agent_instance


def get_llm_monitor() -> LLMResponseMonitor:
    """获取LLM响应监控器"""
    global _llm_monitor_instance
    if _llm_monitor_instance is None:
        agent = get_watcher_agent()
        _llm_monitor_instance = LLMResponseMonitor(agent)
    return _llm_monitor_instance
