"""
gbt/skills/watcher_check.py — 守夜人安全监控
可独立运行: python -m gbt.skills.watcher_check "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class WatcherCheckSkill(Skill):
    name = "watcher_check"
    category = "system"
    description = "守夜人安全监控"
    keywords = ['监控状态', '安全监控', '守夜人', '监控']
    priority = 6
    requires = ['watcher']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.router import router
            w = router.get_dep('watcher')
            result = w.get_status() if hasattr(w, 'get_status') else {'status': 'ok'}
            return SkillResult(True, data=result, message="守夜人监控")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(WatcherCheckSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "守夜人安全监控"
    res = WatcherCheckSkill().run(query)
    print(res.to_dict())
