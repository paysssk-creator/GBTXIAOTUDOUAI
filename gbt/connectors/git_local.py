"""git.py — Local Git connector"""
import subprocess, os

def _git(args, cwd=None, timeout=30):
    r = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return {"ok": r.returncode == 0, "stdout": r.stdout[:5000], "stderr": r.stderr[:1000]}

def git_status(cwd=None): return _git(["status", "--short"], cwd)
def git_log(count=10, cwd=None): return _git(["log", f"--oneline", f"-{count}"], cwd)
def git_diff(cwd=None): return _git(["diff", "--stat"], cwd)

def git_handle(action, **params):
    cwd = params.get("cwd") or os.getcwd()
    handlers = {
        "git_status": lambda: git_status(cwd),
        "git_log": lambda: git_log(params.get("count", 10), cwd),
        "git_diff": lambda: git_diff(cwd),
    }
    h = handlers.get(action)
    if not h: return {"ok": False, "error": f"Unknown action: {action}"}
    try: return h()
    except Exception as e: return {"ok": False, "error": str(e)}
