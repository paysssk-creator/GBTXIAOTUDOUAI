"""
gbt/skills/trade.py — 触发自主交易分析
可独立运行: python -m gbt.skills.trade "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class TradeSkill(Skill):
    name = "trade"
    category = "trading"
    description = "触发自主交易分析"
    keywords = ['买入', '卖出', '买股', '卖股', '交易', '操盘', '下单', 'buy', 'sell']
    priority = 9
    requires = ['trader', 'brain']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.router import router
            brain = router.get_dep('brain')
            result = brain.think(text) if hasattr(brain, 'think') else {'action': 'analyze', 'text': text}
            return SkillResult(True, data=result, message="交易分析")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(TradeSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "触发自主交易分析"
    res = TradeSkill().run(query)
    print(res.to_dict())
