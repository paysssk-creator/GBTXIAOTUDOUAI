# -*- coding: utf-8 -*-
"""gbt/llm_reasoner.py - lightweight LLM action reasoner for TaskEngine.
Uses available LLM keys or returns a fallback action if none configured.
"""
import os, json, logging
from typing import Dict
L = logging.getLogger("GBT.LLMReasoner")

ACTION_PROMPT = """You are an AI computer operator.
Task: {task}
Current screen text (OCR): {observation}
History: {history}
Available action types: click, double_click, move_to, type, hotkey, press, paste, focus_window, launch_app, done.
Return a single JSON object with keys: action_type, params, reasoning.
If the task is finished, set action_type to "done" and params to {{"message": "..."}}.
"""

class LLMActionReasoner:
    def __init__(self):
        self.client = None
        self._llm_failed = False
        self._init_client()

    def _init_client(self):
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            return
        try:
            import openai
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.client = openai.OpenAI(api_key=key, base_url=base)
        except Exception as e:
            L.warning("LLM client init failed: %s", e)

    def reason(self, task: str, observation: str, history: list) -> Dict:
        if self.client is None or self._llm_failed:
            return self._fallback(task, observation)
        prompt = ACTION_PROMPT.format(
            task=task, observation=observation, history=json.dumps(history[-3:], ensure_ascii=False)
        )
        try:
            resp = self.client.chat.completions.create(
                model=os.environ.get("GBT_LLM_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1].replace("json", "").strip()
            action = json.loads(content)
            action.setdefault("reasoning", "llm")
            return action
        except Exception as e:
            L.warning("LLM reason failed: %s", e)
            self._llm_failed = True
            return self._fallback(task, observation)

    def _fallback(self, task: str, observation: str) -> Dict:
        t = task.lower()
        obs = observation.lower()
        if "open chrome" in t or "打开chrome" in t or "打开浏览器" in t:
            if "chrome" in obs:
                return {"action_type": "type", "params": {"text": "https://www.baidu.com"}, "reasoning": "chrome already open, navigate to baidu"}
            return {"action_type": "hotkey", "params": {"keys": ["win", "r"]}, "reasoning": "open run dialog to launch chrome"}
        if "open notepad" in t or "打开记事本" in t:
            return {"action_type": "hotkey", "params": {"keys": ["win", "r"]}, "reasoning": "open run dialog to launch notepad"}
        return {"action_type": "done", "params": {"message": "no LLM key and no matching fallback rule"}, "reasoning": "fallback"}
