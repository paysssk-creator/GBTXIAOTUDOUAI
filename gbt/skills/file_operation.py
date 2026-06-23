"""
gbt/skills/file_operation.py — 文件读写操作
可独立运行: python -m gbt.skills.file_operation "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class FileOperationSkill(Skill):
    name = "file_operation"
    category = "hacker"
    description = "文件读写操作"
    keywords = ['读文件', '写文件', '文件', '代码', '编辑']
    priority = 6
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            result = {'mode': 'file_op', 'text': text}
            return SkillResult(True, data=result, message="文件操作")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(FileOperationSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "文件读写操作"
    res = FileOperationSkill().run(query)
    print(res.to_dict())
