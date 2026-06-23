# -*- coding: utf-8 -*-
"""GBT Packaging Entry - Launches GBT Workstation + Web API"""
import sys, os, threading, webbrowser

# Force UTF-8 to avoid Chinese mojibake in Windows EXE
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

# Determine persistent project home (parent of entry.py)
root_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(root_dir).startswith("_MEI"):
    root_dir = os.path.join(os.environ.get("USERPROFILE", root_dir), "GBTWorkspace")
os.environ.setdefault("GBT_HOME", root_dir)
os.makedirs(root_dir, exist_ok=True)

sys.path.insert(0, root_dir)

# All top-level imports for PyInstaller dependency tracking
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
    """Start Web API service in background"""
    try:
        from gbt.web_api import run_server
        run_server(host="127.0.0.1", port=8765, debug=False)
    except Exception as e:
        print(f"[WebAPI] startup failed: {e}")

# Start desktop workstation
from gbt.desktop_app import GBTWorkstation
if __name__ == '__main__':
    print("GBT Workstation v4 -- Starting...")
    print("[WebAPI] starting at http://127.0.0.1:8765 ...")
    threading.Thread(target=start_web_api, daemon=True).start()

    threading.Thread(target=lambda: webbrowser.open('http://127.0.0.1:8765/'), daemon=True).start()
    GBTWorkstation().r.mainloop()
