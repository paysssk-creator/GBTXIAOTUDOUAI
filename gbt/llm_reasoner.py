# -*- coding: utf-8 -*-
"""gbt/llm_reasoner.py - lightweight LLM action reasoner for TaskEngine.
Uses gbt.key_manager to retrieve keys (env / KeyDB for free / UI prompt for paid).
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

# Provider configs (OpenAI-compatible endpoints)
PROVIDERS = [
    {"pid": "deepseek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"pid": "openclaw", "base_url": "https://openclaw.ai/v1", "model": "gpt-4o-mini"},
    {"pid": "openai",   "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"pid": "gemini",   "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-1.5-flash"},
    {"pid": "groq",     "base_url": "https://api.groq.com/openai/v1", "model": "llama3-8b-8192"},
]


class LLMActionReasoner:
    def __init__(self):
        self.client = None
        self.model = None
        self._llm_failed = False
        self._init_client()

    def _init_client(self):
        from gbt.key_manager import get_key
        for prov in PROVIDERS:
            key = get_key(prov["pid"], prompt=False, allow_save=False)
            if key:
                self._setup_client(key, prov["base_url"], prov["model"])
                L.info("LLM client initialized: %s", prov["pid"])
                return
        L.info("No LLM key available; will use fallback rules")

    def _setup_client(self, key: str, base_url: str, model: str):
        try:
            import openai
            # 5s 连接/读取超时，0 次重试，避免网络抖动时整个 TaskEngine 卡住
            self.client = openai.OpenAI(api_key=key, base_url=base_url, timeout=5, max_retries=0)
            self.model = model
        except Exception as e:
            L.warning("LLM client setup failed: %s", e)

    def reason(self, task: str, observation: str, history: list) -> Dict:
        if self.client is None or self._llm_failed:
            return self._fallback(task, observation)
        prompt = ACTION_PROMPT.format(
            task=task, observation=observation, history=json.dumps(history[-3:], ensure_ascii=False)
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model or os.environ.get("GBT_LLM_MODEL", "gpt-4o-mini"),
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
