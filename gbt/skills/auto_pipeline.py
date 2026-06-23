"""
gbt/skills/auto_pipeline.py — 自主操盘流水线
可独立运行: python -m gbt.skills.auto_pipeline "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class AutoPipelineSkill(Skill):
    name = "auto_pipeline"
    category = "trading"
    description = "自主操盘流水线"
    keywords = ['操盘流水线', '自动操盘', '自主交易']
    priority = 10
    requires = ['trader', 'brain']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.ai_operator import get_ai_operator
            op = get_ai_operator()
            result = op.trade_autonomous('600519')
            return SkillResult(True, data=result, message="自主操盘流水线")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(AutoPipelineSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "自主操盘流水线"
    res = AutoPipelineSkill().run(query)
    print(res.to_dict())
