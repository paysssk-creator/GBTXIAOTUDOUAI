"""
gbt/skills/maximize.py — 最大化/全屏窗口
可独立运行: python -m gbt.skills.maximize "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class MaximizeSkill(Skill):
    name = "maximize"
    category = "desktop"
    description = "最大化/全屏窗口"
    keywords = ['最大化', '全屏', '窗口最大化']
    priority = 5
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.desktop_ctl import desktop_ctl
            desktop_ctl.maximize_window()
            return SkillResult(True, data=result, message="最大化完成")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(MaximizeSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "最大化/全屏窗口"
    res = MaximizeSkill().run(query)
    print(res.to_dict())
