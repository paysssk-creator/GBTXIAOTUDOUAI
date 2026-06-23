"""端到端测试：AI引擎能力"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []

# 1. LLM 核心
try:
    from gbt.llm import GBTLLM
    results.append(("LLM核心", True))
except Exception as e:
    results.append(("LLM核心", str(e)))

# 2. Providers
try:
    from gbt.providers import PROVIDERS
    results.append((f"Providers ({len(PROVIDERS)}个)", True))
except Exception as e:
    results.append(("Providers", str(e)))

# 3. Router
try:
    from gbt.router import router
    results.append(("Router", True))
except Exception as e:
    results.append(("Router", str(e)))

# 4. OpenAI
try:
    import openai
    results.append(("openai库", True))
except Exception as e:
    results.append(("openai库", str(e)))

# 5. Ollama
try:
    import ollama
    results.append(("ollama库", True))
except Exception as e:
    results.append(("ollama库", str(e)))

# 6. tiktoken
try:
    import tiktoken
    results.append(("tiktoken", True))
except Exception as e:
    results.append(("tiktoken", str(e)))

# 7. httpx
try:
    import httpx
    results.append(("httpx", True))
except Exception as e:
    results.append(("httpx", str(e)))

print("=== AI引擎测试 ===")
all_ok = True
for name, ok in results:
    status = "OK" if ok == True else f"FAIL: {ok}"
    if ok != True: all_ok = False
    print(f"  {name}: {status}")
print(f"结果: {'ALL PASS' if all_ok else 'SOME FAILED'}")
sys.exit(0 if all_ok else 1)
