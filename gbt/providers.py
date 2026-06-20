"""
providers.py — GBT 13大模型提供商配置 + 自主密钥发现
"""

import os
from typing import Dict, List, Optional

PROVIDERS: Dict[str, dict] = {
    "zhipu": {"name":"智谱(GLM)","base_url":"https://open.bigmodel.cn/api/paas/v4/",
        "env_keys":["GLM_API_KEY","ZHIPUAI_API_KEY","Z_AI_API_KEY","HERMES_API_KEY"],
        "default_model":"glm-4-flash","models":["glm-4-flash","glm-4-plus","glm-4.5","glm-5-turbo","glm-5.1"],
        "auth_mode":"bearer","guide_url":"https://open.bigmodel.cn/usercenter/apikeys","pricing":"¥10起","tier":1,
        "description":"国产主力LLM，性价比高，中文能力强"},
    "openai": {"name":"OpenAI(GPT)","base_url":"https://api.openai.com/v1/",
        "env_keys":["OPENAI_API_KEY","OPENAI_NATIVE_API_KEY"],
        "default_model":"gpt-4o-mini","models":["gpt-4o-mini","gpt-4o","gpt-5","o4-mini"],
        "auth_mode":"bearer","guide_url":"https://platform.openai.com/api-keys","pricing":"$5起","tier":2,
        "description":"国际标杆，生态最完善"},
    "anthropic": {"name":"Anthropic(Claude)","base_url":"https://api.anthropic.com/v1/",
        "env_keys":["ANTHROPIC_API_KEY","CLAUDE_API_KEY"],
        "default_model":"claude-sonnet-4-20250514","models":["claude-sonnet-4-20250514","claude-opus-4-20250514"],
        "auth_mode":"x-api-key","guide_url":"https://console.anthropic.com/settings/keys","pricing":"$20/月","tier":3,
        "description":"编程能力最强"},
    "gemini": {"name":"Google(Gemini)","base_url":"https://generativelanguage.googleapis.com/v1beta/",
        "env_keys":["GEMINI_API_KEY","GOOGLE_GENERATIVE_AI_API_KEY"],
        "default_model":"gemini-2.5-flash","models":["gemini-2.5-flash","gemini-2.5-pro"],
        "auth_mode":"key","guide_url":"https://aistudio.google.com/apikey","pricing":"免费额度","tier":4,
        "description":"免费大杯，多模态强"},
    "deepseek": {"name":"DeepSeek","base_url":"https://api.deepseek.com/v1/",
        "env_keys":["DEEPSEEK_API_KEY","OPENAI_COMPATIBLE_API_KEY"],
        "default_model":"deepseek-v4-pro","models":["deepseek-v4-pro","deepseek-chat","deepseek-reasoner","deepseek-coder-v2"],
        "auth_mode":"bearer","guide_url":"https://platform.deepseek.com/api_keys","pricing":"送500万tokens","tier":5,
        "description":"国产推理强，R1深度思考"},
    "qwen": {"name":"阿里(Qwen)","base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1/",
        "env_keys":["QWEN_API_KEY","DASHSCOPE_API_KEY"],
        "default_model":"qwen-max","models":["qwen-max","qwen-coder-2.5"],
        "auth_mode":"bearer","guide_url":"https://dashscope.console.aliyun.com/apiKey","pricing":"免费额度","tier":6,
        "description":"国产编码专精"},
    "mistral": {"name":"Mistral","base_url":"https://api.mistral.ai/v1/",
        "env_keys":["MISTRAL_API_KEY"],
        "default_model":"mistral-large-latest","models":["mistral-large-latest","codestral-2405"],
        "auth_mode":"bearer","guide_url":"https://console.mistral.ai/api-keys","pricing":"免费","tier":7,
        "description":"欧洲开源"},
    "grok": {"name":"xAI(Grok)","base_url":"https://api.x.ai/v1/",
        "env_keys":["GROK_API_KEY","XAI_API_KEY"],
        "default_model":"grok-3","models":["grok-3"],
        "auth_mode":"bearer","guide_url":"https://x.ai/api","pricing":"付费","tier":8,
        "description":"马斯克出品"},
    "kimi": {"name":"Kimi(Moonshot)","base_url":"https://api.moonshot.cn/v1/",
        "env_keys":["MOONSHOT_API_KEY","KIMI_API_KEY"],
        "default_model":"moonshot-v1-128k","models":["moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k"],
        "auth_mode":"bearer","guide_url":"https://platform.moonshot.cn/console/api-keys","pricing":"免费","tier":9,
        "description":"超长上下文128K"},
    "stepfun": {"name":"Step-2(阶跃)","base_url":"https://api.stepfun.com/v1/",
        "env_keys":["STEPFUN_API_KEY","STEP_API_KEY"],
        "default_model":"step-2-16k","models":["step-2-16k"],
        "auth_mode":"bearer","guide_url":"https://platform.stepfun.com","pricing":"免费","tier":10,
        "description":"阶跃星辰"},
    "doubao": {"name":"豆包(火山)","base_url":"https://ark.cn-beijing.volces.com/api/v3/",
        "env_keys":["DOUBAO_API_KEY","VOLCENGINE_API_KEY"],
        "default_model":"doubao-pro-32k","models":["doubao-pro-32k"],
        "auth_mode":"bearer","guide_url":"https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey","pricing":"免费","tier":11,
        "description":"字节跳动"},
    "minimax": {"name":"MiniMax","base_url":"https://api.minimax.chat/v1/",
        "env_keys":["MINIMAX_API_KEY"],
        "default_model":"abab6.5s-chat","models":["abab6.5s-chat"],
        "auth_mode":"bearer","guide_url":"https://platform.minimax.chat","pricing":"免费","tier":12,
        "description":"MiniMax"},
    "ollama": {"name":"Ollama(本地)","base_url":"http://localhost:11434/v1/",
        "env_keys":[],"default_model":"qwen2.5-coder:7b",
        "models":["qwen2.5:7b","qwen2.5:14b","llama3.1:8b","deepseek-r1:7b"],
        "auth_mode":"none","guide_url":"https://ollama.com/download","pricing":"免费本地","tier":13,
        "description":"本地运行，隐私安全"},
}

# ── Provider工具函数 ──

def get_provider(pid: str) -> Optional[dict]:
    return PROVIDERS.get(pid)

def list_all() -> List[str]:
    return list(PROVIDERS.keys())

def detect_keys() -> Dict[str, dict]:
    """自动发现环境变量中的API密钥"""
    discovered = {}
    for pid, cfg in PROVIDERS.items():
        found = []
        for ek in cfg["env_keys"]:
            v = os.getenv(ek)
            if v:
                mk = v[:8]+"..."+v[-4:] if len(v)>12 else "***"
                found.append({"key_name":ek,"masked":mk,"raw":v})
        discovered[pid] = {
            "config": cfg,
            "found_keys": found,
            "status": "available" if found else ("check_port" if pid=="ollama" else "missing"),
        }
    return discovered

# ── 自主密钥配置引擎 ──

class AutoKeyConfig:
    """自主密钥配置器 — 自动发现→测试→引导获取"""

    @staticmethod
    def scan() -> Dict[str, dict]:
        """扫描所有提供商状态"""
        return detect_keys()

    @staticmethod
    def get_missing_guide() -> List[dict]:
        """获取缺失密钥的获取指南"""
        guides = []
        discovered = detect_keys()
        for pid, info in discovered.items():
            if info["status"] == "missing":
                cfg = info["config"]
                guides.append({
                    "provider": pid,
                    "name": cfg["name"],
                    "env_key": cfg["env_keys"][0] if cfg["env_keys"] else "N/A",
                    "guide_url": cfg["guide_url"],
                    "pricing": cfg["pricing"],
                    "description": cfg["description"],
                })
        return guides

    @staticmethod
    def check_ollama() -> bool:
        """检测Ollama是否在运行"""
        import socket
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(("localhost", 11434))
            s.close()
            return True
        except:
            return False

