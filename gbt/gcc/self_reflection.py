"""
self_reflection.py — 自省反思循环 (借鉴Cradle Self-Reflection Module)
操作后截图对比 → 判断成功/失败 → 修正策略
"""

import json, time, os, logging
from collections import deque

L = logging.getLogger("GBT.GCC.Reflection")
from typing import Optional, Dict, List

try:
    from ..llm import GBTLLM
except ImportError:
    try:
        from gbt.llm import GBTLLM
    except ImportError:
        GBTLLM = None


class SelfReflectionLoop:
    """自省循环: 执行→截图→对比→判断→重试或继续"""

    MAX_RETRIES = 3

    def __init__(self, llm: Optional[GBTLLM] = None):
        self.llm = llm
        self.history: List[Dict] = []
        self._memory_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reflection_memory.json")
        self._load_memory()

    def _load_memory(self):
        try:
            if os.path.exists(self._memory_path):
                with open(self._memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])[-50:]
        except Exception as e:
            L.debug(f"记忆加载失败: {e}")

    def judge(self, before_b64: Optional[str], after_b64: Optional[str],
              action: Dict, goal: str) -> Dict:
        """判断操作成功与否"""
        if not self.llm:
            return {"success": True, "reasoning": "No LLM, assuming success"}

        msgs = [{"role": "system", "content":
            """对比操作前后的截图, 判断操作是否达到目标。
返回JSON: {"success": true/false, "reasoning": "...", "next_action": "continue/retry/abort"}"""}]

        content = [{"type": "text", "text":
            f"目标: {goal}\n操作: {json.dumps(action, ensure_ascii=False)}\n判断成功?"}]
        if before_b64:
            content.append({"type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{before_b64}"}})
        if after_b64:
            content.append({"type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{after_b64}"}})

        msgs.append({"role": "user", "content": content})

        try:
            raw = self.llm.invoke(msgs)
            s = raw.find("{"); e = raw.rfind("}") + 1
            if s >= 0 and e > s:
                result = json.loads(raw[s:e])
                entry = {"action": action, "result": result, "time": time.time()}
                self.history.append(entry)
                # 持久化记忆
                try:
                    os.makedirs(os.path.dirname(self._memory_path), exist_ok=True)
                    with open(self._memory_path, "w", encoding="utf-8") as f:
                        json.dump({"history": self.history[-50:], "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
                except Exception as e:
                    L.debug(f"记忆持久化失败: {e}")
                return result
            return {"success": True, "reasoning": raw[:200], "next_action": "continue"}
        except Exception as e:
            return {"success": False, "reasoning": str(e), "next_action": "retry"}

    def retry_loop(self, action_fn, before_fn, after_fn,
                   goal: str, max_retries: int = None) -> Dict:
        """重试循环: 执行→判断→重试 直到成功或耗尽"""
        if max_retries is None:
            max_retries = self.MAX_RETRIES

        for attempt in range(max_retries):
            before = before_fn()
            action_fn()
            after = after_fn()

            result = self.judge(before, after, {"attempt": attempt+1}, goal)
            if result.get("success"):
                return {"ok": True, "attempts": attempt+1, **result}
            time.sleep(1)

        return {"ok": False, "attempts": max_retries, "error": "Max retries exceeded"}

    def get_history(self) -> List[Dict]:
        return self.history

    def clear(self):
        self.history = []