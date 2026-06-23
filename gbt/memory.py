"""
memory.py — 记忆系统 (工作记忆/情景记忆/记忆巩固)
基于 hello-agents Memory 模块构建
"""

import json, os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    """记忆条目"""
    key: str
    value: Any
    category: str = "general"  # general | code | fact | user_pref | task
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: int = 1  # 1-5
    access_count: int = 0

    def access(self):
        self.access_count += 1


class MemoryManager:
    """记忆管理器 — 工作记忆 + 情景记忆 + 持久化"""

    def __init__(self, storage_path: Optional[str] = None,
                 working_memory_size: int = 10):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "memory_store.json")
        self.working_memory_size = working_memory_size
        self._working: List[MemoryItem] = []  # 工作记忆(短期)
        self._episodic: List[Dict] = []       # 情景记忆(对话片段)
        self._store: Dict[str, MemoryItem] = {}  # 持久化存储
        self._load()

    def _load(self):
        """从磁盘加载持久记忆"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.get("store", {}).items():
                    self._store[k] = MemoryItem(**v)
                print(f"📦 加载记忆: {len(self._store)} 条")
        except Exception as e:
            print(f"⚠️ 记忆加载失败: {e}")

    def _save(self):
        """持久化到磁盘"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            store_data = {k: {"key": v.key, "value": v.value,
                "category": v.category, "timestamp": v.timestamp,
                "importance": v.importance, "access_count": v.access_count}
                for k, v in self._store.items()}
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({"store": store_data, "updated": datetime.now().isoformat()},
                         f, ensure_ascii=False, indent=2)
        except Exception as e:
            L.warning(f"记忆保存失败: {e}")

    def set(self, key: str, value: Any, category: str = "general",
            importance: int = 1) -> None:
        """存储记忆"""
        item = MemoryItem(key=key, value=value, category=category, importance=importance)
        self._store[key] = item
        self._add_working(item)
        self._save()
        print(f"🧠 记忆: {key}")

    def get(self, key: str) -> Optional[Any]:
        """读取记忆"""
        item = self._store.get(key)
        if item:
            item.access()
            pass  # 读取不触发磁盘写入
            return item.value
        return None

    def search(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """模糊搜索记忆"""
        results = []
        for k, item in self._store.items():
            if category and item.category != category:
                continue
            if query.lower() in k.lower() or (isinstance(item.value, str)
                    and query.lower() in item.value.lower()):
                results.append({"key": k, "value": item.value,
                    "category": item.category, "importance": item.importance})
        return sorted(results, key=lambda x: x["importance"], reverse=True)

    def _add_working(self, item: MemoryItem):
        """添加到工作记忆"""
        self._working.append(item)
        if len(self._working) > self.working_memory_size:
            self._working = self._working[-self.working_memory_size:]

    def get_working_context(self) -> str:
        """获取工作记忆上下文(给LLM用)"""
        if not self._working:
            return ""
        lines = ["## 相关记忆"]
        for item in self._working[-5:]:
            lines.append(f"- [{item.category}] {item.key}: {item.value}")
        return "\n".join(lines)

    def record_episode(self, role: str, content: str) -> None:
        """记录情景记忆"""
        self._episodic.append({
            "role": role, "content": content[:200],
            "timestamp": datetime.now().isoformat()
        })
        if len(self._episodic) > 50:
            self._episodic = self._episodic[-50:]

    def recall_recent(self, n: int = 5) -> List[Dict]:
        """回忆最近情景"""
        return self._episodic[-n:]

    def consolidate(self) -> None:
        """记忆巩固 — 将重要工作记忆持久化"""
        for item in self._working:
            if item.importance >= 3:
                self._store[item.key] = item
        self._save()
        self._working = [i for i in self._working if i.importance < 3]

    def clear(self) -> None:
        """清除所有记忆"""
        self._working.clear()
        self._episodic.clear()
        self._store.clear()
        self._save()

    def stats(self) -> Dict:
        """记忆统计"""
        return {"store": len(self._store), "working": len(self._working),
                "episodic": len(self._episodic)}