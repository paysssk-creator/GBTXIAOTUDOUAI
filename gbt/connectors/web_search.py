"""web_search.py — Web Search connector (DuckDuckGo API)"""
import urllib.request, urllib.parse, json

def search(query, max_results=5):
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.request.quote(query)}&format=json&no_html=1"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("AbstractSource", "DDG"), "snippet": data["AbstractText"][:500], "url": data.get("AbstractURL", "")})
        for t in data.get("RelatedTopics", [])[:max_results]:
            if t.get("Text"):
                results.append({"title": t.get("FirstURL", "").split("/")[-1].replace("_"," "), "snippet": t["Text"][:300], "url": t.get("FirstURL", "")})
        return {"ok": True, "results": results[:max_results]}
    except Exception as e: return {"ok": False, "error": str(e)}

def fetch_page(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GBT/2.1"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"ok": True, "content": r.read().decode("utf-8", errors="replace")[:10000], "status": r.getcode()}
    except Exception as e: return {"ok": False, "error": str(e)}

def ws_handle(action, **params):
    h = {"search": lambda: search(params.get("query",""), params.get("max_results",5)),
         "fetch": lambda: fetch_page(params.get("url",""))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
