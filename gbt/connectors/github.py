"""github.py — GitHub connector (基于 gh CLI)"""
import subprocess, json, os

def _gh(args, timeout=30):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
    return {"ok": r.returncode == 0, "stdout": r.stdout[:5000], "stderr": r.stderr[:1000]}

def _gh_json(args, timeout=30):
    r = subprocess.run(["gh"] + args + ["--json"], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: return {"ok": False, "error": r.stderr[:500]}
    try: return {"ok": True, "data": json.loads(r.stdout)}
    except (json.JSONDecodeError, ValueError): return {"ok": True, "raw": r.stdout[:5000]}

def list_repos(owner=None):
    args = ["repo", "list"] + (["--json", "name,url,language"] if owner else ["--limit", "20"])
    return _gh_json(args) if owner else _gh(["repo", "list", "--limit", "20"])

def search_code(query, lang=None):
    args = ["search", "code", query]
    if lang: args += ["--language", lang]
    return _gh(args + ["--limit", "10"])

def create_pr(title, body="", base="main", head=None):
    if not head:
        r = _gh(["rev-parse", "--abbrev-ref", "HEAD"])
        head = r["stdout"].strip()
    return _gh(["pr", "create", "--title", title, "--body", body or title, "--base", base, "--head", head])

def github_handle(action, **params):
    handlers = {
        "list_repos": lambda: list_repos(params.get("owner")),
        "search_code": lambda: search_code(params.get("query", ""), params.get("lang")),
        "create_pr": lambda: create_pr(params.get("title", ""), params.get("body", ""), params.get("base", "main"), params.get("head")),
    }
    h = handlers.get(action)
    if not h: return {"ok": False, "error": f"Unknown action: {action}"}
    try: return h()
    except FileNotFoundError: return {"ok": False, "error": "gh CLI not installed: winget install GitHub.cli"}
    except Exception as e: return {"ok": False, "error": str(e)}
