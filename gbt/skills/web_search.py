"""
gbt/skills/web_search.py — 网络搜索能力
可独立运行: python -m gbt.skills.web_search "查询内容"
"""
import sys
from .base import Skill, SkillResult, registry


class WebSearchSkill(Skill):
    name = "web_search"
    category = "hacker"
    description = "网络搜索获取实时信息"
    keywords = ["搜索", "查一下", "search", "百度", "谷歌", "搜索新闻"]
    priority = 11

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.scraper import precision_lookup
            result = precision_lookup(text)
            return SkillResult(True, data=result, message="搜索完成")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(WebSearchSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "最新AI新闻"
    res = WebSearchSkill().run(query)
    print(res.to_dict())
