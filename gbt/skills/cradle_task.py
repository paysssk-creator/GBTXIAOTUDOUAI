# -*- coding: utf-8 -*-
"""gbt/skills/cradle_task.py - 电脑自主操控任务能力
优先调用 vendor/cradle runner；若环境不兼容则 fallback 到 GBT TaskEngine。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from .base import Skill, SkillResult, registry
from gbt.adapters.cradle import run_task as cradle_run
from gbt.task_engine import TaskEngine

class CradleTaskSkill(Skill):
    name = "cradle_task"
    category = "desktop"
    description = "AI自主操控电脑执行任务"
    keywords = ["操控电脑", "执行任务", "任务:", "autopilot", "cradle", "打开chrome", "打开记事本", "自主操作", "电脑操作", "自动操盘", "执行一个任务"]
    priority = 9

    def run(self, text: str = "", **kwargs) -> SkillResult:
        task = kwargs.get("task") or text
        env_config = kwargs.get("env_config", "")
        max_steps = kwargs.get("max_steps", 5)
        use_cradle = kwargs.get("use_cradle", True)
        if use_cradle:
            r = cradle_run(task=task, env_config=env_config, max_steps=max_steps)
            if r.get("ok"):
                return SkillResult(True, data=r, message="Cradle 任务执行完成")
        engine = TaskEngine(max_steps=max_steps, safe_mode=False)
        data = engine.run(task)
        return SkillResult(data["ok"], data=data, message="TaskEngine fallback 执行完成")

registry.register(CradleTaskSkill())

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "打开Chrome"
    res = CradleTaskSkill().run(query, use_cradle=False)
    print(res.to_dict())
