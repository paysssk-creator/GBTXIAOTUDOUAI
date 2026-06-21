"""
llm.py — GBT全模型LLM抽象层
基于 hello-agents 模式，支持13大模型 + 自动降级
"""

import os, sys, time, socket
from typing import Optional, List, Dict, Any, Iterator
from openai import OpenAI

from .providers import PROVIDERS, AutoKeyConfig


class GBTLLM:
    """GBT通用LLM客户端 — OpenAI兼容接口 + 多提供商自动切换"""

    def __init__(self, provider: str = "auto", model: Optional[str] = None,
                 api_key: Optional[str] = None, base_url: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 4096, timeout: int = 120, **kwargs):
        # 自动检测或使用指定提供商
        if provider == "auto":
            provider = self._auto_detect()
            if not provider:
                raise ValueError("未检测到可用LLM。请设置环境变量或安装Ollama。"
                               f"运行 AutoKeyConfig.get_missing_guide() 查看获取指南。")

        cfg = PROVIDERS.get(provider)
        if not cfg:
            raise ValueError(f"不支持提供商: {provider}，可选: {list(PROVIDERS.keys())}")

        self.provider = provider
        self.provider_name = cfg["name"]

        # 解析密钥 (多源查找)
        self.api_key = api_key or self._find_key(cfg)
        if not self.api_key and provider != "ollama":
            raise ValueError(f"未找到 {cfg['name']} 的API密钥。"
                           f"请设置 {' 或 '.join(cfg['env_keys'])}")

        # 配置
        self.base_url = base_url or cfg["base_url"]
        self.model = model or cfg["default_model"]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # 创建客户端 (OpenAI兼容)
        client_kw = {"base_url": self.base_url, "timeout": self.timeout}
        if provider == "ollama":
            client_kw["api_key"] = "ollama"
        else:
            client_kw["api_key"] = self.api_key
        self._client = OpenAI(**client_kw)

        print(f"✅ LLM: {cfg['name']} | {self.model}")

    def _find_key(self, cfg: dict) -> Optional[str]:
        """多源查找API密钥"""
        for ek in cfg["env_keys"]:
            v = os.getenv(ek)
            if not v:
                # Fallback: 直接读 .env
                for _p in [os.path.join(os.path.dirname(sys.executable),".env"),
                          os.path.join(sys._MEIPASS,".env") if getattr(sys,'frozen',False) else "",
                          os.path.join(os.path.dirname(__file__),"..",".env"),
                          os.path.join(os.path.dirname(__file__),"..","..",".env")]:
                    if _p and os.path.exists(_p):
                        try:
                            with open(_p,"r",encoding="utf-8") as f:
                                for line in f:
                                    line=line.strip()
                                    if not line or line.startswith("#"): continue
                                    if "=" in line:
                                        kk,vv=line.split("=",1)
                                        if kk.strip()==ek:
                                            v=vv.strip().strip('"').strip("'")
                                            break
                        except Exception:
                            pass  # .env读取失败降级到环境变量
                        if v: break
            if v:
                return v
        if cfg.get("auth_mode") != "none":
            print(f"NO KEY found for {cfg['env_keys']}")
        return None

    def _auto_detect(self) -> Optional[str]:
        """自动检测可用提供商 (按tier优先级, 连接验证)"""
        discovered = AutoKeyConfig.scan()
        available = [pid for pid, info in discovered.items()
                    if info["status"] == "available"]
        # Ollama is most reliable for local dev — prefer if cloud keys fail
        if "ollama" in available:
            # Move ollama to end so cloud providers get tried first
            available.remove("ollama")
            available.append("ollama")
        if not available:
            return None
        # 按tier排序取最优，但添加连接验证
        available.sort(key=lambda p: PROVIDERS[p]["tier"])
        for pid in available:
            if self._test_connection(pid):
                return pid
        return None

    def _test_connection(self, pid: str) -> bool:
        """快速连接测试"""
        import json, urllib.request, urllib.error
        cfg = PROVIDERS.get(pid, {})
        try:
            api_key = self._find_key(cfg) if pid != "ollama" else "ollama"
            headers = {"Content-Type": "application/json"}
            if pid != "ollama":
                headers["Authorization"] = f"Bearer {api_key}"
            model = cfg.get("default_model", "qwen2.5:0.5b")
            data = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "ok"}],
                "max_tokens": 1,
                "stream": False
            }).encode()
            url = cfg["base_url"].rstrip("/") + "/chat/completions"
            req = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.HTTPError as e:
            print(f"  ⚠ {pid} HTTP {e.code}: {e.reason}")
            return False
        except Exception as e:
            print(f"  ⚠ {pid}: {e}")
            return False

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """非流式调用"""
        t = kwargs.get("temperature", self.temperature)
        mt = kwargs.get("max_tokens", self.max_tokens)
        print(f"🧠 [{self.provider_name}] {self.model}...")
        start = time.time()
        try:
            resp = self._client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=t, max_tokens=mt, stream=False)
            content = (resp.choices[0].message.content or "") if resp.choices else ""
            print(f"✅ [{self.provider_name}] {(time.time()-start):.1f}s {len(content)}chars")
            return content
        except Exception as e:
            print(f"❌ [{self.provider_name}] 失败: {e}")
            raise

    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """流式调用"""
        t = kwargs.get("temperature", self.temperature)
        mt = kwargs.get("max_tokens", self.max_tokens)
        print(f"🌊 [{self.provider_name}] 流式 {self.model}...")
        try:
            stream = self._client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=t, max_tokens=mt, stream=True)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"❌ [{self.provider_name}] 流式失败: {e}")
            raise

    def think(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """思考模式 — 流式输出 (hello-agents兼容接口)"""
        full = ""
        print(f"🧠 [{self.provider_name}] 思考中...")
        try:
            for chunk in self.stream_invoke(messages, **kwargs):
                full += chunk
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            print(f"\n❌ 中断: {e}")
        return full

    def list_models(self) -> List[str]:
        return PROVIDERS.get(self.provider, {}).get("models", [])


def create_llm(provider: str = "auto", **kwargs) -> GBTLLM:
    """快速创建LLM客户端"""
    return GBTLLM(provider=provider, **kwargs)