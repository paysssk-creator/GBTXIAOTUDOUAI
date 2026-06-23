"""
gbt/skills/precision_scrape.py — 多源精准资讯抓取交叉验证
可独立运行: python -m gbt.skills.precision_scrape "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class PrecisionScrapeSkill(Skill):
    name = "precision_scrape"
    category = "hacker"
    description = "多源精准资讯抓取交叉验证"
    keywords = ['抓取', '资讯', '新闻', 'scrape']
    priority = 10
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.scraper import precision_lookup
            result = precision_lookup(text)
            return SkillResult(True, data=result, message="精准抓取")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(PrecisionScrapeSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "多源精准资讯抓取交叉验证"
    res = PrecisionScrapeSkill().run(query)
    print(res.to_dict())
