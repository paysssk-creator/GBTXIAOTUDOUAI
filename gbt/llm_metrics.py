"""
llm_metrics.py — LLM消耗追踪引擎 v1.0
Token计数 + 成本计算 + 延迟统计 + 使用历史
"""
import time, threading, json
from collections import deque
from datetime import datetime

MODEL_PRICING = {
    "glm-4-flash":       {"input": 0,    "output": 0,    "desc": "智谱免费"},
    "glm-4-plus":        {"input": 50,   "output": 50,   "desc": "智谱¥50/M"},
    "glm-5.1":           {"input": 100,  "output": 100,  "desc": "智谱¥100/M"},
    "gpt-4o-mini":       {"input": 1.05, "output": 4.2,  "desc": "OpenAI $0.15/$0.6"},
    "gpt-4o":            {"input": 17.5, "output": 70,   "desc": "OpenAI $2.5/$10"},
    "claude-sonnet-4":   {"input": 21,   "output": 105,  "desc": "Anthropic $3/$15"},
    "gemini-2.5-flash":  {"input": 0,    "output": 0,    "desc": "Google免费"},
    "deepseek-chat":     {"input": 1,    "output": 2,    "desc": "DeepSeek ¥1/¥2"},
    "deepseek-reasoner": {"input": 4,    "output": 16,   "desc": "DeepSeek ¥4/¥16"},
    "qwen-max":          {"input": 20,   "output": 60,   "desc": "阿里¥20/¥60"},
    "moonshot-v1-128k":  {"input": 12,   "output": 12,   "desc": "Kimi ¥12/¥12"},
    "doubao-pro-32k":    {"input": 0.8,  "output": 2,    "desc": "豆包¥0.8/¥2"},
    "ollama":            {"input": 0,    "output": 0,    "desc": "本地免费"},
}


class LLMRequest:
    def __init__(self, provider, model, input_tokens, output_tokens, latency):
        self.timestamp = datetime.now().isoformat()
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
        self.latency = latency
        self.cost = self._calc_cost(model, input_tokens, output_tokens)

    def _calc_cost(self, model, inp, out):
        p = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        return inp / 1_000_000 * p["input"] + out / 1_000_000 * p["output"]

    def to_dict(self):
        return {
            "time": self.timestamp[-8:],
            "provider": self.provider, "model": self.model,
            "tokens_in": self.input_tokens, "tokens_out": self.output_tokens,
            "tokens_total": self.total_tokens,
            "latency_s": round(self.latency, 2),
            "cost_rmb": round(self.cost, 4),
        }

class LLMMetrics:
    """LLM消耗追踪器 — 全局单例"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        import threading
        self._lock = threading.Lock()
        self.history = __import__('collections').deque(maxlen=500)
        self.total_requests = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_cost = 0.0
        self.total_latency = 0.0
        self.current_model = ""
        self.current_provider = ""
        self.start_time = time.time()

    def record(self, provider, model, input_tokens, output_tokens, latency):
        req = LLMRequest(provider, model, input_tokens, output_tokens, latency)
        with self._lock:
            self.history.append(req)
            self.total_requests += 1
            self.total_tokens_in += input_tokens
            self.total_tokens_out += output_tokens
            self.total_cost += req.cost
            self.total_latency += latency
            self.current_model = model
            self.current_provider = provider

    def estimate_tokens(self, text):
        if not text: return 0
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other = len(text) - chinese
        return chinese + other // 4

    def get_snapshot(self):
        with self._lock:
            uptime = time.time() - self.start_time
            recent = list(self.history)[-20:]
            return {
                "current": {"provider": self.current_provider, "model": self.current_model},
                "totals": {
                    "requests": self.total_requests,
                    "tokens_in": self.total_tokens_in,
                    "tokens_out": self.total_tokens_out,
                    "tokens_total": self.total_tokens_in + self.total_tokens_out,
                    "cost_rmb": round(self.total_cost, 4),
                    "avg_latency_s": round(self.total_latency / max(self.total_requests, 1), 2),
                },
                "uptime_h": round(uptime / 3600, 1),
                "rpm": round(self.total_requests / max(uptime / 60, 0.1), 1),
                "history": [r.to_dict() for r in recent],
            }


llm_metrics = LLMMetrics()


def record_llm_call(provider, model, prompt_text, response_text, latency):
    m = llm_metrics
    m.record(provider, model, m.estimate_tokens(prompt_text),
             m.estimate_tokens(response_text), latency)


def get_llm_metrics():
    return llm_metrics.get_snapshot()
