"""
gbt/skills/code_exec.py — 执行Python/Shell代码
可独立运行: python -m gbt.skills.code_exec "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class CodeExecSkill(Skill):
    name = "code_exec"
    category = "hacker"
    description = "执行Python/Shell代码"
    keywords = ['执行代码', '运行代码', 'python', 'shell', 'cmd']
    priority = 8
    requires = ['desktop_ctl']

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            result = {'mode': 'code_exec', 'status': 'sandbox only', 'text': text}
            return SkillResult(True, data=result, message="代码执行")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(CodeExecSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "执行Python/Shell代码"
    res = CodeExecSkill().run(query)
    print(res.to_dict())
