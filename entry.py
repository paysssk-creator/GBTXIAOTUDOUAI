"""GBT 打包入口 — 启动真实桌面工作站 + Web API"""
import sys, os, threading

# 强制 UTF-8 编码，避免 Windows EXE 中出现中文乱码
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 全部顶层 import (PyInstaller 追踪依赖)
import gbt
import gbt.llm, gbt.providers, gbt.router, gbt.reasoner
import gbt.guard, gbt.evolve, gbt.mirror, gbt.mcp
import gbt.winctl, gbt.desktop_ctl
import gbt.trader, gbt.strategies, gbt.tech_analysis, gbt.scraper, gbt.backtest, gbt.risk_ctrl
import gbt.agent, gbt.agents, gbt.react, gbt.autopilot
import gbt.memory, gbt.knowledge_base, gbt.database, gbt.keydb, gbt.cloud_kv
import gbt.protocol, gbt.message, gbt.tool
import gbt.watcher, gbt.watcher_agent
import gbt.account, gbt.capabilities, gbt.llm_metrics, gbt.paper_account, gbt.setup_glm4v
import gbt.ai_operator, gbt.web_api
import openai, ollama, tiktoken, httpx
import pyautogui, PIL, pyperclip, psutil
import pyttsx3, speech_recognition
import flask, requests
import tkinter

def start_web_api():
    """后台启动 Web API 服务"""
    try:
        from gbt.web_api import run_server
        run_server(host="127.0.0.1", port=8765, debug=False)
    except Exception as e:
        print(f"[WebAPI] 启动失败: {e}")

# 启动桌面工作站
from gbt.desktop_app import GBTWorkstation
if __name__ == '__main__':
    print("GBT Workstation v4 — Starting...")
    print("[WebAPI] 正在后台启动 http://127.0.0.1:8765 ...")
    threading.Thread(target=start_web_api, daemon=True).start()
    GBTWorkstation().r.mainloop()
