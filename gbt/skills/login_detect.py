"""
gbt/skills/login_detect.py — OCR检测券商登录状态
可独立运行: python -m gbt.skills.login_detect "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class LoginDetectSkill(Skill):
    name = "login_detect"
    category = "desktop"
    description = "OCR检测券商登录状态"
    keywords = ['检测登录', '登录检测', '登录状态']
    priority = 8
    requires = ['desktop_ctl']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.desktop_ctl import desktop_ctl
            result = desktop_ctl.detect_login_state()
            return SkillResult(True, data=result, message="登录检测")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(LoginDetectSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "OCR检测券商登录状态"
    res = LoginDetectSkill().run(query)
    print(res.to_dict())
