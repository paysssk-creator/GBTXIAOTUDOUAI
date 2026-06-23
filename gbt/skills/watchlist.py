"""
gbt/skills/watchlist.py — 查看自选股列表
可独立运行: python -m gbt.skills.watchlist "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class WatchlistSkill(Skill):
    name = "watchlist"
    category = "trading"
    description = "查看自选股列表"
    keywords = ['自选', '自选股', 'watchlist']
    priority = 6
    requires = ['trader']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            trader = router.get_dep('trader')
            wl = getattr(trader, 'WATCHLIST', {})
            result = {'count': len(wl), 'items': list(wl.items())[:10]}
            return SkillResult(True, data=result, message="自选股列表")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(WatchlistSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "查看自选股列表"
    res = WatchlistSkill().run(query)
    print(res.to_dict())
