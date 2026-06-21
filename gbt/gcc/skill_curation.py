"""
skill_curation.py — Skill Curation & Reuse Module
完整吸收 Cradle (BAAI-Agents/Cradle) 的 Skill Curation 能力。

核心功能:
1. 技能提取 — 从成功的 GCC 操作序列中提取可复用技能模板
2. 技能存储 — 持久化到 JSON 文件 (gbt/gcc/skills.json)
3. 技能检索 — 根据任务描述匹配最相关的历史技能
4. 技能复用 — 将历史技能参数适配到新任务
5. 技能评分 — 根据成功率和使用频率给技能打分
"""
import os
import re
import json
import hashlib
import logging
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


# ─── Skill 数据结构 ───────────────────────────────────────────────
@dataclass
class Skill:
    """可复用的操作技能模板"""
    name: str
    description: str
    task_pattern: str                     # 任务匹配模式（关键词）
    actions: List[Dict[str, Any]]         # 操作序列
    success_count: int = 0
    fail_count: int = 0
    last_used: str = ""
    created: str = ""
    tags: List[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """综合评分：成功率 × log(总次数+1)"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        success_rate = self.success_count / total
        return success_rate * (1 + 0.5 * (total ** 0.5))

    @property
    def usage(self) -> int:
        return self.success_count + self.fail_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "task_pattern": self.task_pattern,
            "actions": self.actions,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_used": self.last_used,
            "created": self.created,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Skill":
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            task_pattern=d.get("task_pattern", ""),
            actions=d.get("actions", []),
            success_count=d.get("success_count", 0),
            fail_count=d.get("fail_count", 0),
            last_used=d.get("last_used", ""),
            created=d.get("created", ""),
            tags=d.get("tags", []),
        )


# ─── 技能管理器 ───────────────────────────────────────────────────
class SkillCurator:
    """
    Cradle 技能管理系统。

    生命周期:
    1. extract_skill()   — 从成功的 GCC 操作序列提取 Skill
    2. save_skill()      — 持久化到 skills.json
    3. find_skills()     — 按任务描述检索 Top-K
    4. apply_skill()     — 适配历史技能到新任务
    5. update_score()    — 更新技能评分
    6. get_top_skills()  — 按评分排序返回
    """

    def __init__(self, skill_path: Optional[str] = None):
        if skill_path is None:
            skill_path = os.path.join(os.path.dirname(__file__), "skills.json")
        self.skill_path = skill_path
        self.skills: Dict[str, Skill] = {}
        self._load()

    # ── 持久化 ────────────────────────────────────────────────────
    def _load(self) -> None:
        """从 JSON 文件加载技能库"""
        if not os.path.exists(self.skill_path):
            self.skills = {}
            return
        try:
            with open(self.skill_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    skill = Skill.from_dict(item)
                    self.skills[skill.name] = skill
            elif isinstance(data, dict) and "skills" in data:
                for item in data["skills"]:
                    skill = Skill.from_dict(item)
                    self.skills[skill.name] = skill
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger("GBT.SkillCurator").warning(f"技能文件加载失败: {e}")
            self.skills = {}

    def _save(self) -> None:
        """持久化技能库到 JSON 文件"""
        data = [s.to_dict() for s in self.skills.values()]
        os.makedirs(os.path.dirname(self.skill_path), exist_ok=True)
        with open(self.skill_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 技能提取 ──────────────────────────────────────────────────
    def extract_skill(
        self,
        steps: List[Any],
        task: str,
        success: bool = True,
        min_steps: int = 2,
    ) -> Optional[Skill]:
        """
        从成功的 GCC 操作序列中提取可复用技能。

        Args:
            steps: GCCStep 列表或 dict 列表（含 action/params/success）
            task: 任务描述
            success: 任务是否成功
            min_steps: 最少操作步数才提取

        Returns:
            Skill 或 None（步数不足或失败）
        """
        if not success:
            return None

        # 提取有效操作序列
        actions = []
        for step in steps:
            act = self._extract_action(step)
            if act and act.get("action", "") not in ("wait", "done", "", None):
                actions.append(act)

        if len(actions) < min_steps:
            return None

        # 生成技能名称（基于任务关键词）
        name = self._generate_name(task)
        # 提取任务模式（关键词）
        task_pattern = self._extract_pattern(task)
        # 生成描述
        description = self._summarize(task, actions)

        skill = Skill(
            name=name,
            description=description,
            task_pattern=task_pattern,
            actions=actions,
            success_count=1,
            fail_count=0,
            last_used=datetime.now().isoformat(),
            created=datetime.now().isoformat(),
            tags=self._extract_tags(task),
        )
        return skill

    def _extract_action(self, step: Any) -> Optional[Dict[str, Any]]:
        """从 GCCStep / dict 中提取标准化操作"""
        if hasattr(step, "action") and step.action is not None:
            a = step.action
            return {
                "action": getattr(a, "action", ""),
                "params": getattr(a, "params", {}) or {},
                "reasoning": getattr(a, "reasoning", ""),
            }
        if isinstance(step, dict):
            action = step.get("action", "")
            if isinstance(action, dict):
                return {
                    "action": action.get("action", ""),
                    "params": action.get("params", {}) or {},
                    "reasoning": action.get("reasoning", ""),
                }
            return {
                "action": action if isinstance(action, str) else "",
                "params": step.get("params", {}) or {},
                "reasoning": step.get("reasoning", ""),
            }
        return None

    def _generate_name(self, task: str) -> str:
        """根据任务描述生成技能名称"""
        # 提取中文/英文关键词
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", task)
        key = "_".join(words[:5]) if words else "task"
        # 追加短哈希防冲突
        h = hashlib.md5(task.encode(), usedforsecurity=False).hexdigest()[:6]
        return f"skill_{key}_{h}" if len(key) > 30 else f"skill_{key}"

    def _extract_pattern(self, task: str) -> str:
        """提取任务匹配模式：动词+名词组合"""
        # 中文动词关键词
        cn_verbs = [
            "打开", "关闭", "点击", "输入", "搜索", "下载", "上传",
            "登录", "注册", "切换", "设置", "查看", "删除", "编辑",
            "运行", "安装", "配置", "浏览", "导航", "选择", "提交",
            "保存", "复制", "粘贴", "拖拽", "滚动", "最大化", "最小化",
        ]
        # 英文动词
        en_verbs = [
            "open", "close", "click", "type", "search", "download", "upload",
            "login", "register", "switch", "set", "view", "delete", "edit",
            "run", "install", "configure", "browse", "navigate", "select",
            "submit", "save", "copy", "paste", "drag", "scroll",
        ]
        words = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", task.lower()))
        matched = [w for w in words if w in cn_verbs or w in en_verbs]
        return " ".join(matched) if matched else task[:80]

    def _extract_tags(self, task: str) -> List[str]:
        """从任务中提取标签"""
        words = re.findall(r"[\u4e00-\u9fff]{2,4}|[a-zA-Z]{3,}", task.lower())
        stop = {"the", "and", "for", "from", "with", "that", "this", "will",
                "have", "been", "are", "was", "were", "not", "but", "all",
                "can", "has", "had", "its", "into", "over", "also", "then",
                "的", "了", "是", "在", "和", "也", "就", "都", "而", "及",
                "与", "或", "但", "被", "从", "到", "把", "对", "向", "让"}
        tags = [w for w in set(words) if w not in stop]
        return tags[:8]

    def _summarize(self, task: str, actions: List[Dict]) -> str:
        """生成技能描述"""
        action_types = [a.get("action", "?") for a in actions]
        unique_actions = list(dict.fromkeys(action_types))
        return f"任务: {task[:80]} | 操作: {'→'.join(unique_actions[:6])}"

    # ── 技能存储 ──────────────────────────────────────────────────
    def save_skill(self, skill: Skill) -> bool:
        """
        保存或合并技能。

        同名技能: 合并操作序列（保留更长/更新的），递增计数。
        """
        if not skill or not skill.name:
            return False

        if skill.name in self.skills:
            existing = self.skills[skill.name]
            # 如果新技能操作序列更长，替换
            if len(skill.actions) > len(existing.actions):
                existing.actions = skill.actions
            # 更新描述
            if skill.description:
                existing.description = skill.description
            existing.task_pattern = skill.task_pattern
            existing.tags = list(set(existing.tags + skill.tags))
            existing.success_count += skill.success_count
            existing.fail_count += skill.fail_count
            existing.last_used = skill.last_used
        else:
            self.skills[skill.name] = skill

        self._save()
        return True

    # ── 技能检索 ──────────────────────────────────────────────────
    def find_skills(self, task: str, top_k: int = 3) -> List[Skill]:
        """
        根据任务描述匹配最相关的历史技能。

        使用多维度匹配:
        1. 标签重叠度 (Jaccard)
        2. 任务模式关键词重叠
        3. 描述文本相似度
        """
        if not self.skills:
            return []

        query_tags = set(self._extract_tags(task))
        query_pattern_words = set(re.findall(
            r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", self._extract_pattern(task).lower()
        ))

        scored: List[tuple] = []
        for skill in self.skills.values():
            score = self._match_score(skill, query_tags, query_pattern_words)
            scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k] if _ > 0]

    def _match_score(
        self,
        skill: Skill,
        query_tags: set,
        query_words: set,
    ) -> float:
        """计算技能与查询的匹配得分 (0-1)"""
        # 1) 标签 Jaccard
        skill_tags = set(skill.tags)
        tag_score = _jaccard(query_tags, skill_tags) if query_tags else 0.0

        # 2) 任务模式关键词重叠
        pattern_words = set(re.findall(
            r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", skill.task_pattern.lower()
        ))
        pattern_score = _jaccard(query_words, pattern_words) if query_words else 0.0

        # 3) 描述文本相似度
        desc_words = set(re.findall(
            r"[\u4e00-\u9fff]+|[a-zA-Z]{2,}", skill.description.lower()
        ))
        desc_score = _jaccard(query_words, desc_words) if query_words else 0.0

        # 4) 技能评分加成
        skill_bonus = min(skill.score / 10.0, 0.2)

        return 0.3 * tag_score + 0.35 * pattern_score + 0.35 * desc_score + skill_bonus

    # ── 技能复用 ──────────────────────────────────────────────────
    def apply_skill(self, skill: Skill, task: str) -> Dict[str, Any]:
        """
        将历史技能适配到新任务，返回操作计划。

        Returns:
            {"skill_name": str, "actions": [...], "adapted": bool, "notes": str}
        """
        if not skill or not skill.actions:
            return {"skill_name": "", "actions": [], "adapted": False,
                    "notes": "技能为空"}

        adapted_actions = []
        for act in skill.actions:
            adapted = dict(act)  # 浅拷贝
            # 如果原动作包含绝对坐标，标记为可能需要适配
            params = adapted.get("params", {})
            if "x" in params and "y" in params:
                adapted["_needs_coord_adapt"] = True
            adapted_actions.append(adapted)

        return {
            "skill_name": skill.name,
            "description": skill.description,
            "actions": adapted_actions,
            "adapted": True,
            "notes": f"基于技能 '{skill.name}' (成功{skill.success_count}次) 生成操作计划",
        }

    # ── 技能评分 ──────────────────────────────────────────────────
    def update_score(self, skill_name: str, success: bool) -> bool:
        """更新技能的成功/失败计数"""
        if skill_name not in self.skills:
            return False
        skill = self.skills[skill_name]
        if success:
            skill.success_count += 1
        else:
            skill.fail_count += 1
        skill.last_used = datetime.now().isoformat()
        self._save()
        return True

    # ── 排行 ──────────────────────────────────────────────────────
    def get_top_skills(self, category: str = "", limit: int = 10) -> List[Skill]:
        """
        返回 Top-N 技能（按评分排序）。

        Args:
            category: 可选标签过滤（空字符串表示不过滤）
            limit: 返回数量上限
        """
        candidates = list(self.skills.values())
        if category:
            candidates = [
                s for s in candidates
                if category.lower() in [t.lower() for t in s.tags]
                or category.lower() in s.task_pattern.lower()
            ]
        candidates.sort(key=lambda s: s.score, reverse=True)
        return candidates[:limit]

    # ── 辅助 ──────────────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self.skills)

    def __contains__(self, name: str) -> bool:
        return name in self.skills

    def stats(self) -> Dict[str, Any]:
        """技能库统计"""
        total = len(self.skills)
        if total == 0:
            return {"total_skills": 0, "total_usage": 0, "avg_success_rate": 0.0}
        total_usage = sum(s.usage for s in self.skills.values())
        total_success = sum(s.success_count for s in self.skills.values())
        total_attempts = total_success + sum(s.fail_count for s in self.skills.values())
        avg_sr = total_success / total_attempts if total_attempts > 0 else 0.0
        return {
            "total_skills": total,
            "total_usage": total_usage,
            "avg_success_rate": round(avg_sr, 3),
        }


# ─── 全局单例 ─────────────────────────────────────────────────────
_curator: Optional[SkillCurator] = None
_curator_lock = threading.Lock()


def get_curator(skill_path: Optional[str] = None) -> SkillCurator:
    """获取全局 SkillCurator 单例"""
    global _curator
    if _curator is None:
        with _curator_lock:
            if _curator is None:
                _curator = SkillCurator(skill_path=skill_path)
    return _curator


# ─── 工具函数 ─────────────────────────────────────────────────────
def _jaccard(a: set, b: set) -> float:
    """Jaccard 相似度"""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
