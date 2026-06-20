"""
protocol.py — GBT 执行协议 v1.0
每条能力调用都经过: 意图→路由→确认→执行→验证→响应
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
import logging, time, json

L = logging.getLogger("GBT.Protocol")

# ═══════════════════════════════════════════════════════
# 错误等级
# ═══════════════════════════════════════════════════════
class ErrorLevel(Enum):
    L1_RETRY   = "retry"      # 重试一次即可
    L2_FALLBACK = "fallback"  # 降级处理
    L3_ALERT   = "alert"      # 需人工干预

# ═══════════════════════════════════════════════════════
# 执行阶段
# ═══════════════════════════════════════════════════════
class Phase(Enum):
    INTENT    = "intent"       # 意图识别
    ROUTE     = "route"         # 路由匹配
    ACK       = "acknowledge"   # 能力确认
    PRE_CHECK = "pre_check"     # 依赖检查
    EXECUTE   = "execute"       # 实际执行
    VERIFY    = "verify"        # 结果验证
    RESPOND   = "respond"       # 响应输出

# ═══════════════════════════════════════════════════════
# 请求/响应数据结构
# ═══════════════════════════════════════════════════════
@dataclass
class ExecutionRequest:
    """标准化执行请求"""
    intent: str                          # 用户/系统意图文本
    source: str = "user"                 # user | brain | watcher | cron
    priority: int = 5                    # 1-10, 10=紧急
    context: Dict[str, Any] = field(default_factory=dict)  # 附加上下文
    trace_id: str = ""                   # 链路追踪ID

@dataclass
class ExecutionResult:
    """标准化执行结果"""
    ok: bool = False
    capability: str = ""
    trace_id: str = ""                    # 链路追踪ID
    phase_results: Dict[str, Any] = field(default_factory=dict)  # 每阶段结果
    data: Dict[str, Any] = field(default_factory=dict)           # 返回数据
    errors: List[str] = field(default_factory=list)
    error_level: Optional[ErrorLevel] = None
    elapsed_ms: float = 0
    meta: Dict[str, Any] = field(default_factory=dict)

# ═══════════════════════════════════════════════════════
# 验证规则注册表
# ═══════════════════════════════════════════════════════
VERIFICATION_RULES: Dict[str, Callable] = {}

def register_verification(capability_name: str, rule: Callable):
    """注册验证规则: 返回 (ok: bool, detail: str)"""
    VERIFICATION_RULES[capability_name] = rule

def verify(capability_name: str, result_data: Dict, dependencies: Dict) -> tuple:
    """执行验证: 返回 (ok: bool, detail: str)"""
    rule = VERIFICATION_RULES.get(capability_name)
    if rule:
        return rule(result_data, dependencies)
    # 默认验证: 检查返回结构是否符合基本schema
    if not isinstance(result_data, dict):
        return False, "default: result is not a dict"
    if not result_data:
        return False, "default: empty dict"
    return True, "default: valid dict with data"

# ═══════════════════════════════════════════════════════
# 执行协议核心
# ═══════════════════════════════════════════════════════
class ExecutionProtocol:
    """GBT 执行协议 — 结构化每次能力调用"""

    def __init__(self, router_ref=None):
        self.router = router_ref              # SmartRouter 引用 (延迟注入)
        self._exec_count = 0
        self._history = []                     # 最近执行记录

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """主入口: 完整协议链路执行"""
        t0 = time.time()
        result = ExecutionResult(
            trace_id=f"gex-{int(t0*1000)}-{self._exec_count}",
            meta={"started": time.strftime('%H:%M:%S')})
        self._exec_count += 1

        # ── Phase 1: INTENT ──
        result.phase_results[Phase.INTENT.value] = {
            "ok": True, "intent": request.intent[:100], "source": request.source}

        # ── Phase 2: ROUTE ──
        cap = None
        classification = None
        if self.router:
            classification = self.router.classify(request.intent)
            cap = classification.get("capability") if classification else None
        result.phase_results[Phase.ROUTE.value] = {
            "ok": cap is not None, "capability": cap.name if cap else None}

        # ── Phase 3: ACK ──
        if cap and cap.handler:
            result.capability = cap.name
            result.phase_results[Phase.ACK.value] = {
                "ok": True, "capability": cap.name, "category": cap.category}
        else:
            result.phase_results[Phase.ACK.value] = {"ok": False, "reason": "no handler"}
            result.errors.append("no capability matched")
            result.error_level = ErrorLevel.L2_FALLBACK
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        # ── Phase 4: PRE_CHECK ──
        deps_ok, dep_detail = self._check_dependencies(cap)
        result.phase_results[Phase.PRE_CHECK.value] = {"ok": deps_ok, "detail": dep_detail}
        if not deps_ok:
            result.errors.append(f"dependencies missing: {dep_detail}")
            result.error_level = ErrorLevel.L2_FALLBACK
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        # ── Phase 5: EXECUTE ──
        try:
            raw = cap.handler(request.intent)
            result.phase_results[Phase.EXECUTE.value] = {"ok": True, "raw_len": len(str(raw))}
        except Exception as e:
            L.error(f"执行异常 [{cap.name}]: {e}")
            result.phase_results[Phase.EXECUTE.value] = {"ok": False, "error": str(e)[:100]}
            result.errors.append(f"execution failed: {str(e)[:80]}")
            result.error_level = ErrorLevel.L1_RETRY
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        # ── Phase 6: VERIFY ──
        deps = {}
        if self.router:
            for dep_name in cap.requires:
                deps[dep_name] = self.router.get_dep(dep_name)
        v_ok, v_detail = verify(cap.name, {"result": raw}, deps)
        result.phase_results[Phase.VERIFY.value] = {"ok": v_ok, "detail": v_detail}
        if not v_ok:
            result.errors.append(f"verification failed: {v_detail}")
            result.error_level = ErrorLevel.L2_FALLBACK

        # ── Phase 7: RESPOND ──
        result.data = {
            "conclusion": raw if isinstance(raw, str) else str(raw),
            "capability": cap.name,
            "category": cap.category}
        result.ok = len(result.errors) == 0
        result.phase_results[Phase.RESPOND.value] = {"ok": result.ok}
        result.elapsed_ms = (time.time() - t0) * 1000

        # 记录历史
        self._history.append({
            "trace_id": result.trace_id,
            "capability": result.capability,
            "ok": result.ok,
            "elapsed_ms": result.elapsed_ms})
        if len(self._history) > 100:
            self._history = self._history[-50:]

        return result

    def _check_dependencies(self, cap) -> tuple:
        """检查能力依赖是否就绪"""
        if not cap.requires:
            return True, "no dependencies"
        missing = []
        for dep in cap.requires:
            if not self.router or not self.router.get_dep(dep):
                missing.append(dep)
        if missing:
            return False, f"missing: {', '.join(missing)}"
        return True, f"{len(cap.requires)} deps ready"

    def get_stats(self):
        """协议执行统计"""
        if not self._history:
            return {"executions": 0, "success_rate": 1.0}
        ok_count = sum(1 for h in self._history if h["ok"])
        return {
            "executions": len(self._history),
            "success_rate": round(ok_count / len(self._history), 3),
            "avg_elapsed_ms": round(sum(h["elapsed_ms"] for h in self._history) / len(self._history), 1),
            "last_5": self._history[-5:]
        }


# 全局协议实例
protocol = ExecutionProtocol()
