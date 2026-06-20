"""terminal.py — Terminal connector (安全命令执行)"""
import subprocess, shlex, os

def exec_cmd(cmd, cwd=None, timeout=30):
    if isinstance(cmd, str):
        parts = shlex.split(cmd)
    else:
        parts = cmd
    if not parts: return {"ok": False, "error": "Empty command"}
    try:
        r = subprocess.run(parts, shell=False, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"ok": r.returncode == 0, "stdout": r.stdout[:5000], "stderr": r.stderr[:1000], "code": r.returncode}
    except subprocess.TimeoutExpired: return {"ok": False, "error": "Timeout"}
    except FileNotFoundError: return {"ok": False, "error": f"Command not found: {parts[0]}"}
    except Exception as e: return {"ok": False, "error": str(e)}

def shell_cmd(cmd, cwd=None, timeout=30):
    return exec_cmd(cmd, cwd, timeout)

def terminal_handle(action, **params):
    handlers = {
        "exec": lambda: exec_cmd(params.get("cmd", ""), params.get("cwd"), params.get("timeout", 30)),
        "shell": lambda: shell_cmd(params.get("cmd", ""), params.get("cwd"), params.get("timeout", 30)),
    }
    h = handlers.get(action)
    if not h: return {"ok": False, "error": f"Unknown action: {action}"}
    return h()
