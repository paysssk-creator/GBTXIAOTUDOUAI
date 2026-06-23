"""
gbt/skills/system_status.py — 查看GBT系统状态
可独立运行: python -m gbt.skills.system_status "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class SystemStatusSkill(Skill):
    name = "system_status"
    category = "system"
    description = "查看GBT系统状态"
    keywords = ['系统状态', '运行状态', '状态']
    priority = 6
    requires = ['brain']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.router import router
            lines = []
            brain = router.get_dep('brain')
            trader = router.get_dep('trader')
            watcher = router.get_dep('watcher')
            if brain and hasattr(brain, 'get_status'): lines.append(f'大脑: {brain.get_status()}')
            if trader: lines.append(f"交易: {len(getattr(trader, 'WATCHLIST', {}))} 自选")
            if watcher and hasattr(watcher, 'get_status'): lines.append(f'监控: {watcher.get_status()}')
            result = '\n'.join(lines)
            return SkillResult(True, data=result, message="系统状态")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(SystemStatusSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "查看GBT系统状态"
    res = SystemStatusSkill().run(query)
    print(res.to_dict())
