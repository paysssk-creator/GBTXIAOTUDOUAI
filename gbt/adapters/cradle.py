"""
gbt/adapters/cradle.py — Cradle 核心操控适配器
Cradle 子模块已挂到 vendor/cradle，
本适配器负责调用 Cradle runner 实现电脑自主操控。
"""
import os, subprocess, sys, logging, json
from typing import Dict
L = logging.getLogger("GBT.Adapter.Cradle")
CRADLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vendor", "cradle")
RUNNER = os.path.join(CRADLE_DIR, "runner.py")
_proc = None
def is_available() -> bool:
    return os.path.exists(RUNNER)
def run_task(task: str = "open chrome and search GBT", max_steps: int = 10, env_config: str = "") -> Dict:
    if not is_available():
        return {"ok": False, "error": f"runner.py not found at {RUNNER}"}
    env = os.environ.copy()
    env["PYTHONPATH"] = CRADLE_DIR
    cmd = [sys.executable, RUNNER]
    if env_config:
        cmd += ["--envConfig", env_config]
    try:
        # 子进程超时留 5s 缓冲，避免 Flask HTTP 请求先超时
        p = subprocess.run(cmd, cwd=CRADLE_DIR, env=env, capture_output=True, text=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout[:2000], "stderr": p.stderr[:1000], "task": task}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "cradle runner timed out after 25s", "task": task}
    except Exception as e:
        return {"ok": False, "error": str(e)}
def status() -> Dict:
    return {"ok": True, "available": is_available(), "path": CRADLE_DIR}
