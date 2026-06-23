# -*- coding: utf-8 -*-
"""gbt/task_engine.py - Real autonomous computer control task engine.
Observes screen -> reasons next action via LLM/fallback -> executes via AIDeviceOperator.
"""
import os, sys, json, time, logging
from typing import Dict, List
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
L = logging.getLogger("GBT.TaskEngine")

from gbt.ai_operator import DeviceAction
from gbt.llm_reasoner import LLMActionReasoner


class TaskEngine:
    def __init__(self, max_steps: int = 10, safe_mode: bool = False):
        from gbt.ai_operator import AIDeviceOperator
        self.operator = AIDeviceOperator(safe_mode=safe_mode)
        self.max_steps = max_steps
        self.safe_mode = safe_mode
        self.reasoner = LLMActionReasoner()

    def run(self, task: str) -> Dict:
        history: List[Dict] = []
        for step in range(self.max_steps):
            obs = self.operator.observe(use_llm=False)
            obs_summary = obs.get("text", "")[:500]
            action = self.reasoner.reason(task, obs_summary, history)
            if action.get("action_type") == "done" or action.get("done"):
                history.append({"step": step, "observation": obs_summary, "action": "done", "result": action})
                break
            # Ensure required keys for DeviceAction
            action.setdefault("reasoning", "")
            result = self.operator.act(DeviceAction(**action))
            history.append({"step": step, "observation": obs_summary, "action": action, "result": result})
            time.sleep(0.5)
        return {"ok": True, "task": task, "steps": len(history), "history": history}


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "open chrome"
    engine = TaskEngine(max_steps=5, safe_mode=False)
    result = engine.run(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))
