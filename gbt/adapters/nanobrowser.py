"""
gbt/adapters/nanobrowser.py — Nanobrowser 启动/状态适配器
Nanobrowser 子模块已挂到 vendor/nanobrowser，
本适配器负责从 GBT 主程序启动/停止/查询 nanobrowser。
"""
import os, subprocess, sys, logging, time
from typing import Dict

L = logging.getLogger("GBT.Adapter.Nanobrowser")

NB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vendor", "nanobrowser")
NB_PY = os.path.join(NB_DIR, "nanobrowser.py")

_proc = None


def is_available() -> bool:
    return os.path.exists(NB_PY)


def start() -> Dict:
    global _proc
    if not is_available():
        return {"ok": False, "error": f"nanobrowser.py not found at {NB_PY}"}
    if _proc is not None and _proc.poll() is None:
        return {"ok": True, "status": "already_running", "pid": _proc.pid}
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        _proc = subprocess.Popen(
            [sys.executable, NB_PY],
            cwd=NB_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        time.sleep(1)
        status = "started" if _proc.poll() is None else "failed"
        return {"ok": status == "started", "status": status, "pid": _proc.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop() -> Dict:
    global _proc
    if _proc is None:
        return {"ok": True, "status": "not_running"}
    try:
        _proc.terminate()
        _proc.wait(timeout=3)
        return {"ok": True, "status": "stopped", "pid": _proc.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def status() -> Dict:
    if _proc is None:
        return {"ok": True, "status": "not_running"}
    running = _proc.poll() is None
    return {"ok": True, "status": "running" if running else "exited", "pid": _proc.pid}
