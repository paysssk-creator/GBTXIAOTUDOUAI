"""
gbt/skills/notify.py — 发送Windows桌面通知
可独立运行: python -m gbt.skills.notify "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class NotifySkill(Skill):
    name = "notify"
    category = "notification"
    description = "发送Windows桌面通知"
    keywords = ['通知', '提醒我', '提醒', '弹窗']
    priority = 4
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.desktop_ctl import desktop_ctl
            desktop_ctl.notify('GBT', text)
            return SkillResult(True, data=result, message="通知已发送")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(NotifySkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "发送Windows桌面通知"
    res = NotifySkill().run(query)
    print(res.to_dict())
