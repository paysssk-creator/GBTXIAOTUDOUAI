"""github.py — GitHub connector (REST API + gh CLI fallback)"""
import subprocess, json, os
try:
    import urllib.request as _req
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

GITHUB_API = "https://api.github.com"

def _gh(args, timeout=30):
    """gh CLI fallback"""
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
    return {"ok": r.returncode == 0, "stdout": r.stdout[:5000], "stderr": r.stderr[:1000]}

def _gh_json(args, timeout=30):
    r = subprocess.run(["gh"] + args + ["--json"], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: return {"ok": False, "error": r.stderr[:500]}
    try: return {"ok": True, "data": json.loads(r.stdout)}
    except (json.JSONDecodeError, ValueError): return {"ok": True, "raw": r.stdout[:5000]}

def _has_gh():
    """Check if gh CLI is installed and authenticated"""
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

def _rest(path, timeout=15):
    """Direct GitHub REST API call — no auth needed for public endpoints"""
    req = _req.Request(f"{GITHUB_API}{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "GBT-Pro"})
    r = _req.urlopen(req, timeout=timeout)
    return json.loads(r.read().decode())

def list_repos(owner=None):
    # Try gh CLI first for authenticated access (higher rate limit)
    if _has_gh():
        args = ["repo", "list"] + (["--json", "name,url,language"] if owner else ["--limit", "20"])
        return _gh_json(args) if owner else _gh(["repo", "list", "--limit", "20"])
    # Fallback: REST API (public repos only, unauthenticated)
    if owner:
        data = _rest(f"/users/{owner}/repos?per_page=20&sort=updated")
        repos = [{"name": r["name"], "url": r["html_url"], "language": r.get("language", "N/A")} for r in data]
        return {"ok": True, "data": repos}
    return {"ok": False, "error": "GitHub: 未登录gh CLI，请指定owner参数"}

def search_code(query, lang=None):
    if _has_gh():
        args = ["search", "code", query]
        if lang: args += ["--language", lang]
        return _gh(args + ["--limit", "10"])
    # REST fallback
    q = query + (f"+language:{lang}" if lang else "")
    data = _rest(f"/search/code?q={_req.quote(q)}&per_page=10")
    items = [{"repo": i["repository"]["full_name"], "path": i["path"]} for i in data.get("items", [])]
    return {"ok": True, "stdout": json.dumps(items, indent=2)[:5000], "stderr": ""}

def create_pr(title, body="", base="main", head=None):
    if not _has_gh():
        return {"ok": False, "error": "PR创建需要gh CLI认证: gh auth login"}
    if not head:
        r = _gh(["rev-parse", "--abbrev-ref", "HEAD"])
        head = r["stdout"].strip()
    return _gh(["pr", "create", "--title", title, "--body", body or title, "--base", base, "--head", head])

def get_user(username):
    """获取GitHub用户公开信息（免费，无需认证）"""
    data = _rest(f"/users/{username}")
    return {"ok": True, "data": {
        "name": data.get("name", ""), "bio": data.get("bio", ""),
        "repos": data.get("public_repos", 0), "followers": data.get("followers", 0),
        "avatar": data.get("avatar_url", ""), "blog": data.get("blog", "")
    }}

def trending():
    """GitHub trending (via gh CLI search, free)"""
    if not _has_gh():
        return {"ok": False, "error": "需要gh CLI: winget install GitHub.cli; gh auth login"}
    return _gh(["search", "repos", "stars:>1000", "--sort", "stars", "--limit", "10"])

def github_handle(action, **params):
    handlers = {
        "list_repos": lambda: list_repos(params.get("owner")),
        "search_code": lambda: search_code(params.get("query", ""), params.get("lang")),
        "create_pr": lambda: create_pr(params.get("title", ""), params.get("body", ""), params.get("base", "main"), params.get("head")),
        "get_user": lambda: get_user(params.get("username", "")),
        "trending": trending,
    }
    h = handlers.get(action)
    if not h: return {"ok": False, "error": f"Unknown action: {action}"}
    try: return h()
    except _req.HTTPError as e:
        return {"ok": False, "error": f"GitHub API {e.code}: {e.reason}"}
    except Exception as e: return {"ok": False, "error": str(e)}
