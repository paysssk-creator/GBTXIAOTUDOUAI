"""pypi.py — PyPI connector"""
import urllib.request, json

def search_packages(query):
    try:
        url = f"https://pypi.org/pypi?%3Aaction=search&term={urllib.request.quote(query)}&submit="
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = [{"name": p["name"], "version": p["version"], "summary": p.get("summary", "")} for p in data.get("results", [])[:10]]
        return {"ok": True, "results": results}
    except Exception as e: return {"ok": False, "error": str(e)}

def package_info(name):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=10) as r:
            data = json.loads(r.read())
        info = data.get("info", {})
        return {"ok": True, "name": info.get("name"), "version": info.get("version"),
                "summary": info.get("summary"), "url": info.get("home_page")}
    except Exception as e: return {"ok": False, "error": str(e)}

def pypi_handle(action, **params):
    handlers = {"search": lambda: search_packages(params.get("query", "")),
                "info": lambda: package_info(params.get("name", ""))}
    h = handlers.get(action)
    return h() if h else {"ok": False, "error": f"Unknown action: {action}"}
