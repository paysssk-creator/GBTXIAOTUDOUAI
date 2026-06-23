# -*- coding: utf-8 -*-
"""gbt/key_manager.py - Secure key manager with UI prompt.
Free-tier keys can be persisted in KeyDB.
Paid keys are prompted via a native input window and are NOT persisted by default.
"""
import os, sys, logging
from typing import Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

L = logging.getLogger("GBT.KeyManager")

# Provider metadata: free keys are persisted; paid keys prompt by default.
PROVIDER_REGISTRY = {
    "deepseek": {"env": "DEEPSEEK_API_KEY", "name": "DeepSeek", "free": False},
    "openclaw": {"env": "OPENCLAW_API_KEY", "name": "OpenClaw/OpenRouter", "free": True},
    "openai":   {"env": "OPENAI_API_KEY",   "name": "OpenAI",   "free": False},
    "anthropic":{"env": "ANTHROPIC_API_KEY","name": "Claude",   "free": False},
    "gemini":   {"env": "GEMINI_API_KEY",   "name": "Gemini",   "free": True},
    "groq":     {"env": "GROQ_API_KEY",     "name": "Groq",     "free": True},
    "mistral":  {"env": "MISTRAL_API_KEY",  "name": "Mistral",  "free": True},
    "kimi":     {"env": "MOONSHOT_API_KEY", "name": "Kimi",     "free": True},
    "stepfun":  {"env": "STEPFUN_API_KEY",  "name": "StepFun",  "free": True},
    "doubao":   {"env": "DOUBAO_API_KEY",   "name": "Doubao",   "free": True},
    "cohere":   {"env": "COHERE_API_KEY",   "name": "Cohere",   "free": True},
    "together": {"env": "TOGETHER_API_KEY", "name": "Together", "free": True},
    "zhipu":    {"env": "GLM_API_KEY",      "name": "Zhipu GLM","free": True},
    "qwen":     {"env": "QWEN_API_KEY",     "name": "Qwen",     "free": True},
}


def _prompt_tk(title: str, message: str, show: str = "*") -> Optional[str]:
    """Native tkinter password/input prompt. Returns None if cancelled."""
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.lift()
        value = simpledialog.askstring(title, message, show=show, parent=root)
        root.destroy()
        return value
    except Exception as e:
        L.warning("tk prompt failed: %s", e)
        return None


def _prompt_cli(title: str, message: str) -> Optional[str]:
    """Fallback command-line prompt."""
    print(f"\n[{title}] {message}")
    try:
        return input("Key: ").strip()
    except EOFError:
        return None


def prompt_key(provider: str, message: str = None, allow_save: bool = False) -> Optional[str]:
    """Prompt user for an API key via UI (or CLI fallback).
    allow_save: if True and provider is free-tier, offer to persist in KeyDB.
    """
    meta = PROVIDER_REGISTRY.get(provider, {"name": provider, "free": False})
    title = f"{meta['name']} API Key"
    msg = message or f"请输入 {meta['name']} API Key"
    value = _prompt_tk(title, msg) or _prompt_cli(title, msg)
    if not value:
        return None
    if allow_save and meta.get("free"):
        try:
            from gbt.keydb import KeyDB
            KeyDB().save(provider, value, free=True, note="user prompted")
            L.info("Free-tier key persisted for %s", provider)
        except Exception as e:
            L.warning("Failed to persist free key: %s", e)
    return value


def get_key(provider: str, prompt: bool = True, allow_save: bool = False) -> Optional[str]:
    """Get key with priority: env var -> KeyDB (free) -> UI prompt.
    paid providers: prompted, not persisted.
    free providers: prompted with option to persist.
    """
    meta = PROVIDER_REGISTRY.get(provider, {"env": f"{provider.upper()}_API_KEY", "free": False})
    env_key = os.environ.get(meta["env"])
    if env_key:
        return env_key

    if meta.get("free"):
        try:
            from gbt.keydb import KeyDB
            key = KeyDB().get(provider)
            if key:
                return key
        except Exception as e:
            L.debug("KeyDB read failed: %s", e)

    if prompt:
        return prompt_key(provider, allow_save=allow_save)
    return None


def set_env_key(provider: str, key: str):
    """Set key in current process environment (not persisted to disk)."""
    meta = PROVIDER_REGISTRY.get(provider, {"env": f"{provider.upper()}_API_KEY"})
    os.environ[meta["env"]] = key


def save_free_key(provider: str, key: str):
    """Explicitly save a free-tier key to KeyDB."""
    if not PROVIDER_REGISTRY.get(provider, {}).get("free"):
        L.warning("Refusing to persist paid key for %s", provider)
        return False
    try:
        from gbt.keydb import KeyDB
        KeyDB().save(provider, key, free=True, note="explicit save")
        return True
    except Exception as e:
        L.error("Failed to save free key: %s", e)
        return False


if __name__ == "__main__":
    # Demo: prompt for a key
    key = get_key("deepseek", prompt=True, allow_save=False)
    print("got key:", bool(key))
