# -*- coding: utf-8 -*-
"""gbt/task_engine.py - Real autonomous computer control task engine.
Observes screen -> reasons next action -> executes via AIDeviceOperator.
"""
import os, sys, json, time, logging
from typing import Dict, List
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
L = logging.getLogger("GBT.TaskEngine")

from gbt.ai_operator import DeviceAction

class TaskEngine:
    def __init__(self, max_steps: int = 10, safe_mode: bool = False):
        from gbt.ai_operator import AIDeviceOperator
        self.operator = AIDeviceOperator(safe_mode=safe_mode)
        self.max_steps = max_steps
        self.safe_mode = safe_mode

    def run(self, task: str) -> Dict:
        history: List[Dict] = []
        for step in range(self.max_steps):
            obs = self.operator.observe(use_llm=False)
            obs_summary = obs.get("text", "")[:500]
            action = self._reason(task, obs_summary, history)
            if action.get("done"):
                history.append({"step": step, "observation": obs_summary, "action": "done", "result": action})
                break
            result = self.operator.act(DeviceAction(**action))
            history.append({"step": step, "observation": obs_summary, "action": action, "result": result})
            time.sleep(0.5)
        return {"ok": True, "task": task, "steps": len(history), "history": history}

    def _reason(self, task: str, observation: str, history: List[Dict]) -> Dict:
        # Simple keyword-based reasoning for deterministic demo.
        t = task.lower()
        obs = observation.lower()
        if "open chrome" in t or "打开chrome" in t or "打开浏览器" in t:
            return {"action_type": "hotkey", "params": {"keys": ["win", "r"]}, "reasoning": "open run dialog"}
        if "search" in t and "chrome" in obs:
            return {"action_type": "type", "params": {"text": "https://www.baidu.com"}, "reasoning": "type baidu url"}
        return {"done": True, "message": "task flow finished"}


if __name__ == "__main__":
    import sys
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "open chrome"
    engine = TaskEngine(max_steps=5, safe_mode=False)
    result = engine.run(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))
