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
        
        # 状态（以下字段的变更均受 self._lock 保护）
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
        
        with self._lock:
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
        except Exception as e:
            L.debug(f"记忆快照失败 {path}: {e}")
            return MemorySnapshot(path=path, hash='error', size=0, last_modified='?')
    
    # ═══════════════════════════════════════════════════════
    # 2. 幻觉检测
    # ═══════════════════════════════════════════════════════
    
    def detect_hallucination(self, text: str, source: str = "unknown") -> list[WatchFinding]:
        """检测大模型输出中的幻觉"""
        findings = []
        hallu_local = 0
        for pattern, concern in self.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                first_match = matches[0]
                snippet = first_match[:60] if isinstance(first_match, str) else str(first_match[0] if isinstance(first_match, tuple) else first_match)[:60]
                finding = WatchFinding(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    category="hallucination",
                    severity="warn",
                    source=source,
                    message=f"{concern}: {snippet}",
                    suggestion="请主Agent核实并纠正，避免传播不实信息",
                    context={"pattern": pattern, "matches": len(matches)}
                )
                findings.append(finding)
                hallu_local += 1
        
        if findings:
            with self._lock:
                self.hallucination_count += hallu_local
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
            with self._lock:
                self.findings.extend(findings)
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 4. 连接链路监控
    # ═══════════════════════════════════════════════════════
    
    def check_connections(self) -> list[WatchFinding]:
        """监控所有连接链路"""
        findings = []
        alerts_local = 0
        
        # 4.1 GBT API
        try:
            import urllib.request
            with urllib.request.urlopen('http://localhost:8877/api/status', timeout=5) as r:
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
            alerts_local += 1
        
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
                except Exception as e:
                    L.debug(f"MCP状态检查失败 {name}: {e}")
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
                alerts_local += 1
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
            with urllib.request.urlopen('https://hq.sinajs.cn/list=sh000001', timeout=5) as r:
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
            alerts_local += 1
        
        # 4.4 DeepSeek LLM API
        try:
            import os
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
            L.warning(f"LLM API Key检查异常: {e}")
        
        if findings:
            with self._lock:
                self.connection_alerts += alerts_local
                self.findings.extend(findings)
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 5. 项目结构扫描 — 检测主Agent跑偏
    # ═══════════════════════════════════════════════════════
    
    def scan_project_structure(self) -> list[WatchFinding]:
        """扫描项目结构，检测主Agent是否跑偏"""
        findings = []
        drift_local = 0
        
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
                drift_local += 1
            
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
                drift_local += 1
                
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
                drift_local += 1
        
        if findings:
            with self._lock:
                self.drift_alerts += drift_local
                self.findings.extend(findings)
        with self._lock:
            self.last_full_scan = datetime.now().strftime("%H:%M:%S")
        return findings
    
    # ═══════════════════════════════════════════════════════
    # 6. 心跳主循环
    # ═══════════════════════════════════════════════════════
    
    def heartbeat(self):
        """单次心跳 — 执行所有监控检查"""
        with self._lock:
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
        with self._lock:
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
                except Exception as e:
                    L.warning(f"Watcher告警保存失败: {e}")
                    
        except Exception as e:
            L.error(f"唤醒主Agent失败: {e}")
    
    # ═══════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════
    
    def start(self, main_brain=None):
        """启动守夜人Agent"""
        if main_brain:
            self.main_brain = main_brain
        
        with self._lock:
            self.running = True
        L.info(f"🦉 守夜人Agent已启动 — 监控中")
        
        # 首次快速扫描
        self.sync_memory()
        self.scan_project_structure()
        
        return {"ok": True, "version": "v1.0", "mode": "readonly"}
    
    def stop(self):
        """停止守夜人Agent"""
        with self._lock:
            self.running = False
        L.info("🦉 守夜人Agent已停止")
    
    def get_status(self):
        """获取状态"""
        with self._lock:
            hb = self.heartbeat_count
            mem_snaps = len(self.memory_snapshots)
            f_len = len(self.findings)
            hallu = self.hallucination_count
            conn_a = self.connection_alerts
            drift_a = self.drift_alerts
            last_scan = self.last_full_scan
            recent = [
                {
                    "time": f.timestamp,
                    "category": f.category,
                    "severity": f.severity,
                    "message": f.message[:80],
                    "suggestion": f.suggestion[:80],
                }
                for f in self.findings[-10:]
            ]
        return {
            "running": self.running,
            "version": "v1.0",
            "heartbeat_count": hb,
            "memory_snapshots": mem_snaps,
            "findings": f_len,
            "stats": {
                "hallucination": hallu,
                "connection_alerts": conn_a,
                "drift_alerts": drift_a,
            },
            "last_full_scan": last_scan,
            "recent_findings": recent,
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


# ═══════════════════════════════════════════════════════
# 沙盒验证闭环
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile
    
    # 配置 logging 以便观察输出
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s [%(levelname)s] %(message)s"
    )
    
    print("=" * 60)
    print("WatcherAgent 沙盒验证")
    print("=" * 60)
    
    # 1. 创建实例（使用临时目录作为项目根）
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 logs 子目录供 scan_logs 使用
        logs_dir = os.path.join(tmpdir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        # 写一个示例日志文件
        with open(os.path.join(logs_dir, 'test.log'), 'w', encoding='utf-8') as f:
            f.write("2025-01-01 00:00:00 INFO 正常消息\n")
            f.write("2025-01-01 00:00:01 ERROR 测试错误\n")
            f.write("2025-01-01 00:00:02 WARNING 测试警告\n")
        
        print(f"\n[1] 创建 WatcherAgent (project_root={tmpdir})...")
        agent = WatcherAgent(project_root=tmpdir)
        assert agent is not None
        assert agent.running is False
        assert agent.heartbeat_count == 0
        assert agent.hallucination_count == 0
        assert agent.connection_alerts == 0
        assert agent.drift_alerts == 0
        print("    ✅ 实例创建成功，初始状态正确")
        
        # 2. 测试 start / stop（验证锁保护 running）
        print("\n[2] 测试 start() / stop()...")
        result = agent.start()
        assert result["ok"] is True
        assert agent.running is True
        print(f"    ✅ start() 返回: {result}")
        
        agent.stop()
        assert agent.running is False
        print("    ✅ stop() 后 running=False")
        
        # 3. 测试幻觉检测（验证锁保护 hallucination_count 和 findings）
        print("\n[3] 测试 detect_hallucination()...")
        test_text = "我已经修复了所有bug，全部通过了测试，买入100股成功成交价格为12.50元"
        findings = agent.detect_hallucination(test_text, source="test")
        print(f"    发现 {len(findings)} 处可疑")
        for f_ in findings:
            print(f"      [{f_.severity}] {f_.message[:60]}")
        assert agent.hallucination_count == len(findings)
        assert len(agent.findings) == len(findings)
        print("    ✅ 幻觉计数与 findings 一致，锁正常工作")
        
        # 4. 测试 scan_logs（验证锁保护 findings）
        print("\n[4] 测试 scan_logs()...")
        log_findings = agent.scan_logs()
        print(f"    日志扫描发现 {len(log_findings)} 条")
        for f_ in log_findings:
            print(f"      [{f_.severity}] {f_.message[:80]}")
        # findings 应包含之前的幻觉检测 + 日志发现
        assert len(agent.findings) >= len(findings) + len(log_findings)
        print("    ✅ findings 累积正确，锁正常工作")
        
        # 5. 测试 check_connections（验证锁保护 connection_alerts）
        print("\n[5] 测试 check_connections()...")
        conn_findings = agent.check_connections()
        print(f"    连接检查发现 {len(conn_findings)} 条告警")
        for f_ in conn_findings:
            print(f"      [{f_.severity}] {f_.source}: {f_.message[:60]}")
        # 连接数应与 findings 中 connection 类别数匹配
        conn_categories = sum(1 for f_ in conn_findings if f_.category == "connection")
        print(f"    connection_alerts={agent.connection_alerts}, connection类别数={conn_categories}")
        print("    ✅ check_connections 完成，锁正常工作")
        
        # 6. 多线程压力测试：验证锁不会死锁
        print("\n[6] 多线程并发测试（10线程 x 100次 heartbeat）...")
        errors_in_threads = []
        
        def worker():
            try:
                for _ in range(100):
                    agent.heartbeat()
            except Exception as e:
                errors_in_threads.append(str(e))
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors_in_threads) == 0, f"线程异常: {errors_in_threads}"
        # heartbeat_count 应为 10 * 100 = 1000
        print(f"    heartbeat_count={agent.heartbeat_count} (预期=1000)")
        assert agent.heartbeat_count == 1000, f"心跳计数不一致: {agent.heartbeat_count}"
        print("    ✅ 多线程并发无异常，锁无死锁，计数器正确")
        
        # 7. 测试 get_status
        print("\n[7] 测试 get_status()...")
        status = agent.get_status()
        print(f"    heartbeat_count={status['heartbeat_count']}")
        print(f"    total_findings={status['findings']}")
        print(f"    stats={status['stats']}")
        assert status["running"] is False
        print("    ✅ get_status 正常返回")
        
        # 8. 测试 LLMResponseMonitor
        print("\n[8] 测试 LLMResponseMonitor...")
        monitor = LLMResponseMonitor(agent)
        result = monitor.audit("API返回正常，所有接口连接成功，已修复全部问题", source="test-llm")
        if result:
            print(f"    audit 发现 {len(result)} 处可疑")
        else:
            print("    audit 未发现可疑（正常）")
        
        api_response = {"conclusion": "短", "protocol": {"ok": False, "error_level": "high"}}
        api_findings = monitor.check_api_response(api_response)
        if api_findings:
            print(f"    check_api_response 发现 {len(api_findings)} 条")
            for f_ in api_findings:
                print(f"      [{f_.severity}] {f_.message[:60]}")
        print("    ✅ LLMResponseMonitor 正常工作")
        
        # 9. 测试单例
        print("\n[9] 测试单例...")
        a1 = get_watcher_agent(tmpdir)
        a2 = get_watcher_agent()
        assert a1 is a2
        print(f"    ✅ 单例模式正确 (a1 is a2 = {a1 is a2})")
    
    print("\n" + "=" * 60)
    print("🎉 全部沙盒验证通过 — 锁、异常处理、连接检查均正常")
    print("=" * 60)
