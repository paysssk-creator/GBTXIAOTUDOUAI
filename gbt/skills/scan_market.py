"""
gbt/skills/scan_market.py — 扫描全市场/自选股
可独立运行: python -m gbt.skills.scan_market "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class ScanMarketSkill(Skill):
    name = "scan_market"
    category = "trading"
    description = "扫描全市场/自选股"
    keywords = ['扫描', '全市场', '自选股']
    priority = 7
    requires = ['trader']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            result = {'ok': True, 'capability': 'market_scan', 'text': text}
            return SkillResult(True, data=result, message="市场扫描")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(ScanMarketSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "扫描全市场/自选股"
    res = ScanMarketSkill().run(query)
    print(res.to_dict())
