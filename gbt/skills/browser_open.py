"""
gbt/skills/browser_open.py — 浏览器控制能力
可独立运行: python -m gbt.skills.browser_open https://example.com
"""
import sys
import re
from .base import Skill, SkillResult, registry


class BrowserOpenSkill(Skill):
    name = "browser_open"
    category = "desktop"
    description = "打开浏览器/网页"
    keywords = ["打开浏览器", "打开edge", "打开chrome", "打开网页", "上网", "浏览", "browser"]
    priority = 9

    def run(self, text: str = "", **kwargs) -> SkillResult:
        url = kwargs.get("url")
        if not url:
            m = re.search(r"(https?://\S+)", text)
            url = m.group(1) if m else "https://www.baidu.com"
        try:
            import webbrowser
            webbrowser.open(url)
            return SkillResult(True, data={"url": url}, message=f"已打开 {url}")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(BrowserOpenSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "打开百度"
    res = BrowserOpenSkill().run(query)
    print(res.to_dict())
