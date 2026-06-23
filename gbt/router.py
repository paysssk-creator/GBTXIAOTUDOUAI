"""
router.py — GBT 智能调度路由器
统一能力注册表 + 意图分类 + 自主路由
大脑不是被动等指令，而是主动判断"该用什么能力"
"""
import os, sys, time, re, json, logging

L = logging.getLogger("GBT.Router")

class Capability:
    """能力描述"""
    def __init__(self, name, category, description, keywords=None,
                 handler=None, priority=5, requires=None):
        self.name = name
        self.category = category  # desktop | trading | query | system | reasoning | notification
        self.description = description
        self.keywords = keywords or []
        self.handler = handler      # callable that executes the capability
        self.priority = priority    # 1-10, higher = more eager to use
        self.requires = requires or []  # ["trader","account",...]

    def matches(self, text):
        """Check if this capability matches the user intent"""
        t = text.lower()
        return any(kw in t for kw in self.keywords)

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "keywords": self.keywords[:5],
            "priority": self.priority,
        }


class SmartRouter:
    """智能调度路由器 — 统一入口，自主分发"""

    def __init__(self):
        self.capabilities = {}
        self._handlers = {}  # name -> handler function
        self._deps = {}      # name -> required objects

    def register(self, cap: Capability):
        """注册一个能力"""
        self.capabilities[cap.name] = cap
        if cap.handler:
            self._handlers[cap.name] = cap.handler
        L.debug(f"Registered: {cap.name} [{cap.category}] p={cap.priority}")

    def set_dependency(self, name, obj):
        """注入依赖对象 (trader, watcher, account, desktop_ctl, llm)"""
        self._deps[name] = obj

    def get_dep(self, name):
        return self._deps.get(name)

    def set_protocol(self, protocol):
        """注入执行协议"""
        self._protocol = protocol
        protocol.router = self

    def route_protocol(self, text: str, source: str = "user", priority: int = 5) -> dict:
        """协议链路执行: 意图→路由→确认→预检→执行→验证→响应"""
        from gbt.protocol import ExecutionRequest
        req = ExecutionRequest(intent=text, source=source, priority=priority)
        result = self._protocol.execute(req) if hasattr(self, '_protocol') and self._protocol else None
        if not result:
            return self.route(text)  # fallback to legacy
        # 构造兼容旧格式的 result
        cap = self.capabilities.get(result.capability)
        return {
            # 旧格式兼容
            "routed": result.ok or result.capability != "",
            "classification": {
                "intent": text[:50],
                "confidence": cap.priority * 10 if cap else 50,
                "capability": cap,
                "alternatives": []
            },
            "execution": {
                "ok": result.ok,
                "result": result.data.get("conclusion", ""),
                "capability": result.capability,
                "executed": result.ok
            },
            "action": "executed" if result.ok else "protocol_error",
            # 新增协议字段
            "protocol": {
                "ok": result.ok,
                "capability": result.capability,
                "phases": result.phase_results,
                "errors": result.errors,
                "elapsed_ms": result.elapsed_ms,
                "error_level": result.error_level.value if result.error_level else None,
                "trace_id": result.trace_id,
            }
        }

    def classify(self, text: str) -> dict:
        """分类用户意图 → 返回最佳匹配能力 + 置信度"""
        if not text or not text.strip():
            return {"intent": "unknown", "confidence": 0, "capability": None}

        matches = []
        for cap in self.capabilities.values():
            if cap.matches(text):
                # 越长的关键词匹配权重越高
                best_kw = max((kw for kw in cap.keywords if kw in text.lower()), key=len, default="")
                score = len(best_kw) / max(len(text), 1) * cap.priority
                matches.append((score, cap))

        if not matches:
            return {"intent": "unknown", "confidence": 0, "capability": None,
                    "suggestion": "fallback_to_reasoning"}

        matches.sort(key=lambda x: x[0], reverse=True)
        best_score, best_cap = matches[0]
        confidence = min(100, int(best_score * 100))

        return {
            "intent": best_cap.name,
            "category": best_cap.category,
            "confidence": confidence,
            "capability": best_cap,
            "alternatives": [m[1].name for m in matches[1:4]],
        }

    def execute(self, capability_name: str, *args, **kwargs) -> dict:
        """执行指定能力"""
        handler = self._handlers.get(capability_name)
        if not handler:
            return {"ok": False, "error": f"能力 {capability_name} 无执行函数", "executed": False}
        try:
            result = handler(*args, **kwargs)
            return {"ok": True, "result": result, "capability": capability_name, "executed": True}
        except Exception as e:
            L.error(f"执行 {capability_name} 失败: {e}")
            return {"ok": False, "error": str(e), "capability": capability_name, "executed": False}

    def route(self, text: str) -> dict:
        """智能路由: 分类 → 执行 → 返回结果"""
        classification = self.classify(text)

        if classification["capability"] is None:
            # 无法匹配 → 回退到 LLM 推理
            return {
                "routed": False,
                "classification": classification,
                "action": "fallback_reasoning",
            }

        cap = classification["capability"]

        # 检查依赖是否满足
        for req in cap.requires:
            if self._deps.get(req) is None:
                L.warning(f"能力 {cap.name} 需要 {req} 但未注入")
                return {
                    "routed": False,
                    "classification": classification,
                    "action": "missing_dependency",
                    "missing": req,
                }

        # 执行能力
        exec_result = self.execute(cap.name, text)
        return {
            "routed": True,
            "classification": classification,
            "execution": exec_result,
            "action": "executed",
        }

    def list_capabilities(self):
        """列出所有已注册能力"""
        return {name: cap.to_dict() for name, cap in self.capabilities.items()}

    def get_capability_context(self) -> str:
        """生成 LLM 可用的能力上下文文本"""
        lines = ["## 可用能力清单"]
        by_cat = {}
        for cap in self.capabilities.values():
            by_cat.setdefault(cap.category, []).append(cap)

        for cat, caps in sorted(by_cat.items()):
            lines.append(f"\n### {cat}")
            for c in sorted(caps, key=lambda x: x.priority, reverse=True):
                lines.append(f"- **{c.name}**: {c.description} (触发词: {', '.join(c.keywords[:3])})")

        return "\n".join(lines)


# ── 全局路由器实例 ──
router = SmartRouter()
