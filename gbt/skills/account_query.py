"""
gbt/skills/account_query.py — 查看模拟账户
可独立运行: python -m gbt.skills.account_query "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class AccountQuerySkill(Skill):
    name = "account_query"
    category = "system"
    description = "查看模拟账户"
    keywords = ['账户', '资金', '余额', '持仓', '仓位']
    priority = 6
    requires = ['account']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.router import router
            acc = router.get_dep('account')
            result = acc.snapshot() if hasattr(acc, 'snapshot') else {'balance': 100000}
            return SkillResult(True, data=result, message="账户信息")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(AccountQuerySkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "查看模拟账户"
    res = AccountQuerySkill().run(query)
    print(res.to_dict())
