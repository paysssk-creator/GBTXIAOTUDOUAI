# -*- coding: utf-8 -*-
"""
gbt/op_memory.py — 操作记忆桥 v1.0

连接"知识库"和"能力执行"，让 GBT 记住自己的每一步操作:

能力链路: 意图 → 路由 → 执行 → 结果 → [操作记忆记录] → 下次决策可参考

三层记忆:
  work_memory   — 当前会话的最后 N 次操作 (自动窗口)
  episodic      — 完整操作历史 (可检索)
  learned       — 从反复操作中提炼的模式
"""

import os, json, time, logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import deque

L = logging.getLogger("GBT.OpMemory")


@dataclass
class OpRecord:
    """单次操作记录"""
    capability: str     # 能力名
    intent: str         # 原始意图文本
    result: str         # 执行结果 (截断 200 字符)
    ok: bool           # 是否成功
    elapsed_ms: float  # 耗时 ms
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = ""

    def age_seconds(self) -> float:
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return (datetime.now() - dt).total_seconds()
        except Exception:
            return 0

    def to_context(self) -> str:
        """转为 LLM 可读的上文"""
        ago = int(self.age_seconds())
        ago_str = f"{ago}s前" if ago < 120 else f"{ago//60}分钟前"
        status = "✓" if self.ok else "✗"
        return f"[{ago_str}] {status} {self.capability}: {self.result[:80]}"


class OperationalMemory:
    """操作记忆引擎"""

    MAX_WORKING = 20          # 工作记忆窗口大小
    MAX_LEARNED_PATTERNS = 50  # 学习模式上限

    def __init__(self, storage_dir: str = ""):
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data"
        )
        os.makedirs(self.storage_dir, exist_ok=True)

        self._path = os.path.join(self.storage_dir, "op_memory.json")
        self.working: deque[OpRecord] = deque(maxlen=self.MAX_WORKING)
        self.episodic: List[OpRecord] = []
        self.learned: Dict[str, int] = {}   # capability_name → 累计使用次数
        self._session_start = datetime.now().isoformat()

        self._load()

    # ── 记录 ──

    def record(
        self,
        capability: str,
        intent: str,
        result: str,
        ok: bool,
        elapsed_ms: float = 0,
    ) -> OpRecord:
        """记录一次操作"""
        r = OpRecord(
            capability=capability,
            intent=intent[:100],
            result=str(result)[:200],
            ok=ok,
            elapsed_ms=elapsed_ms,
        )
        self.working.append(r)
        self.episodic.append(r)

        # 更新学习计数
        self.learned[capability] = self.learned.get(capability, 0) + 1

        # 每 10 次操作后持久化
        if len(self.episodic) % 10 == 0:
            self._save()

        return r

    # ── 检索 ──

    def recent(self, n: int = 5) -> List[OpRecord]:
        """最近 N 次操作"""
        return list(self.working)[-n:]

    def recent_context(self, n: int = 5) -> str:
        """最近 N 次操作作为 LLM 上下文"""
        records = self.recent(n)
        if not records:
            return "(尚无操作记录)"
        lines = ["=== 最近操作 ==="]
        for r in records:
            lines.append(r.to_context())
        return "\n".join(lines)

    def search(self, query: str, top_k: int = 5) -> List[OpRecord]:
        """在操作历史中搜索 (关键词/能力名)"""
        query_lower = query.lower()
        matches = []
        for r in reversed(self.episodic[-200:]):  # 只搜最近 200 条
            score = 0
            if query_lower in r.capability.lower():
                score += 3
            if query_lower in r.intent.lower():
                score += 2
            if query_lower in r.result.lower():
                score += 1
            if score > 0:
                matches.append((score, r))
        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:top_k]]

    def last_of(self, capability: str) -> Optional[OpRecord]:
        """上次执行某个能力的记录"""
        for r in reversed(self.working):
            if r.capability == capability:
                return r
        return None

    def stats(self) -> dict:
        """操作统计"""
        ok_count = sum(1 for r in self.working if r.ok)
        fail_count = len(self.working) - ok_count
        # 能力使用排行
        usage = sorted(self.learned.items(), key=lambda x: -x[1])
        return {
            "total_ops": len(self.episodic),
            "working_size": len(self.working),
            "ok_rate": f"{ok_count}/{len(self.working)}" if self.working else "0/0",
            "top_capabilities": [{"name": n, "count": c} for n, c in usage[:10]],
            "session_start": self._session_start,
            "last_op_ago": int(self.recent(1)[0].age_seconds()) if self.working else -1,
        }

    def summary(self) -> str:
        """人类可读的操作摘要"""
        if not self.working:
            return "尚未执行任何操作。"

        s = self.stats()
        lines = [
            f"📊 操作记忆: {s['total_ops']} 次操作 (本会话 {len(self.working)} 次)",
            f"✅ 成功率: {s['ok_rate']}",
            "",
            "📋 最近 8 次操作:",
        ]
        for r in self.recent(8):
            status_icon = "✅" if r.ok else "❌"
            lines.append(f"  {status_icon} {r.capability}: {r.result[:60]}")
        return "\n".join(lines)

    def context_for_decision(self) -> str:
        """生成供决策参考的上下文 (注入 LLM prompt)"""
        parts = []

        # 最近操作
        recent = self.recent(5)
        if recent:
            parts.append("你最近执行了以下操作 (请参考以避免重复):")
            for r in recent:
                status = "成功" if r.ok else "失败"
                parts.append(f"  - {r.capability}({status}): {r.result[:80]}")
            parts.append("")

        # 上次失败的能力
        failed = [r for r in self.working if not r.ok]
        if failed:
            parts.append("以下能力上次执行失败，请考虑替代方案:")
            for r in failed[-3:]:
                parts.append(f"  - {r.capability}: {r.result[:60]}")
            parts.append("")

        # 高频操作建议
        top3 = sorted(self.learned.items(), key=lambda x: -x[1])[:3]
        if top3:
            parts.append("你最常用的能力:")
            for name, count in top3:
                parts.append(f"  - {name} (已使用 {count} 次)")
            parts.append("")

        return "\n".join(parts) if parts else ""

    # ── 持久化 ──

    def _save(self):
        """保存到磁盘"""
        try:
            data = {
                "updated": datetime.now().isoformat(),
                "session_start": self._session_start,
                "learned": self.learned,
                "episodic": [
                    {
                        "capability": r.capability,
                        "intent": r.intent[:100],
                        "result": r.result[:200],
                        "ok": r.ok,
                        "elapsed_ms": r.elapsed_ms,
                        "timestamp": r.timestamp,
                    }
                    for r in self.episodic[-200:]  # 只保留最近 200 条
                ],
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            L.debug(f"操作记忆保存失败: {e}")

    def _load(self):
        """从磁盘加载"""
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.learned = data.get("learned", {})
                self._session_start = data.get("session_start", self._session_start)
                # 加载情景记忆（不放入工作窗口，工作窗口仅保留当前会话的）
                for item in data.get("episodic", [])[-50:]:
                    self.episodic.append(OpRecord(
                        capability=item.get("capability", ""),
                        intent=item.get("intent", ""),
                        result=item.get("result", ""),
                        ok=item.get("ok", True),
                        elapsed_ms=item.get("elapsed_ms", 0),
                        timestamp=item.get("timestamp", ""),
                    ))
                L.info(f"操作记忆加载: {len(self.episodic)} 条历史")
        except Exception as e:
            L.debug(f"操作记忆加载失败: {e}")


# ═══════════════════════════════════════════════════════
# 与路由器集成 — 自动记录每次能力执行
# ═══════════════════════════════════════════════════════

_op_memory: Optional[OperationalMemory] = None


def get_op_memory() -> OperationalMemory:
    global _op_memory
    if _op_memory is None:
        _op_memory = OperationalMemory()
    return _op_memory


def record_from_route(intent: str, route_result: dict, elapsed_ms: float = 0):
    """从路由结果自动记录操作 (供 router/start_demo 调用)"""
    om = get_op_memory()
    exe = route_result.get("execution", {})
    cap_name = exe.get("capability", route_result.get("capability", ""))
    if hasattr(cap_name, "name"):
        cap_name = cap_name.name
    if not cap_name:
        classification = route_result.get("classification", {})
        cap_obj = classification.get("capability")
        if hasattr(cap_obj, "name"):
            cap_name = cap_obj.name
    result = str(exe.get("result", route_result.get("action", "")))
    ok = exe.get("ok", route_result.get("routed", False))
    om.record(
        capability=str(cap_name),
        intent=intent[:100],
        result=result,
        ok=bool(ok),
        elapsed_ms=elapsed_ms,
    )


L.info("GBT 操作记忆桥 v1.0 已就绪")
