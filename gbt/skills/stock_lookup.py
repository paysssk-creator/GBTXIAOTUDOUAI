"""
gbt/skills/stock_lookup.py — 查询股票实时行情
可独立运行: python -m gbt.skills.stock_lookup "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class StockLookupSkill(Skill):
    name = "stock_lookup"
    category = "trading"
    description = "查询股票实时行情"
    keywords = ['股票', '行情', '股价', '600519']
    priority = 8
    requires = ['trader']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.router import router
            import re
            m = re.search(r'(?<!\\d)(\\d{6})(?!\\d)', text)
            code = m.group(1) if m else '600519'
            trader = router.get_dep('trader')
            q = trader.fetch_quote([code])
            qt = q.get(code)
            name = getattr(qt, 'name', code)
            price = getattr(qt, 'price', 0)
            pct = getattr(qt, 'change_pct', 0)
            result = f'{name}({code}): ¥{price} | {pct:+.2f}%'
            return SkillResult(True, data=result, message="股票行情")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(StockLookupSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "查询股票实时行情"
    res = StockLookupSkill().run(query)
    print(res.to_dict())
