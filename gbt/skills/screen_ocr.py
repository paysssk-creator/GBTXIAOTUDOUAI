"""
gbt/skills/screen_ocr.py — 屏幕 OCR 能力
可独立运行: python -m gbt.skills.screen_ocr
"""
import sys
from .base import Skill, SkillResult, registry


class ScreenOCRSkill(Skill):
    name = "screen_ocr"
    category = "desktop"
    description = "屏幕 OCR 识别桌面文字"
    keywords = ["ocr", "识别屏幕", "看屏幕", "读屏幕", "屏幕文字", "识图", "ocr识别"]
    priority = 7

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.ai_operator import get_ai_operator
            op = get_ai_operator()
            result = op.observe(use_llm=False)
            return SkillResult(True, data=result, message="屏幕 OCR 完成")
        except Exception as e:
            return SkillResult(False, error=str(e))


# 注册到统一注册表
registry.register(ScreenOCRSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "ocr"
    res = ScreenOCRSkill().run(query)
    print(res.to_dict())
