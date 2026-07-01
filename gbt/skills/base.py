"""
gbt/skills/base.py — Skill 基类与统一注册表
借鉴 open-strix 的 skill 组织方式：
- 每个 skill 是独立模块
- 既能被 SmartRouter 统一调度
- 也能通过 `python -m gbt.skills.<name> "query"` 独立运行
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

L = logging.getLogger("GBT.Skill")


class SkillResult:
    """统一的 skill 执行结果"""
    def __init__(self, ok: bool, data: Any = None, message: str = "", error: str = ""):
        self.ok = ok
        self.data = data
        self.message = message
        self.error = error

    def to_dict(self) -> Dict:
        return {"ok": self.ok, "data": self.data, "message": self.message, "error": self.error}


class Skill(ABC):
    """能力模块基类"""
    name: str = ""
    category: str = ""
    description: str = ""
    keywords: List[str] = []
    priority: int = 5
    requires: List[str] = []

    @abstractmethod
    def run(self, text: str = "", **kwargs) -> SkillResult:
        """执行能力"""
        pass

    def match(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.keywords)

    def to_capability_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "keywords": self.keywords[:5],
            "priority": self.priority,
        }


class SkillRegistry:
    """Skill 统一注册表"""
    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def register(self, skill: Skill):
        self.skills[skill.name] = skill
        L.debug(f"Skill registered: {skill.name}")

    def find(self, text: str) -> List[Skill]:
        return [s for s in self.skills.values() if s.match(text)]

    def run(self, name: str, text: str = "", **kwargs) -> SkillResult:
        skill = self.skills.get(name)
        if not skill:
            return SkillResult(False, error=f"Skill '{name}' not found")
        try:
            return skill.run(text, **kwargs)
        except Exception as e:
            L.exception(f"Skill {name} failed")
            return SkillResult(False, error=str(e))

    def list(self) -> List[Dict]:
        return [s.to_capability_dict() for s in self.skills.values()]


# 全局 skill 注册表
registry = SkillRegistry()
