"""
gbt/skills/screenshot.py — 屏幕截图
可独立运行: python -m gbt.skills.screenshot "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class ScreenshotSkill(Skill):
    name = "screenshot"
    category = "desktop"
    description = "屏幕截图"
    keywords = ['截图', '截屏', 'screen']
    priority = 6
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            import pyautogui, time
            ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'screenshots')
            os.makedirs(ss_dir, exist_ok=True)
            fp = os.path.join(ss_dir, f'screenshot_{time.strftime("%Y%m%d_%H%M%S")}.png')
            pyautogui.screenshot(fp)
            return SkillResult(True, data=result, message="截图已保存")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(ScreenshotSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "屏幕截图"
    res = ScreenshotSkill().run(query)
    print(res.to_dict())
