"""filesystem.py — File System connector"""
import os, json, glob as _glob

def read_file(path, max_lines=200):
    if not os.path.exists(path): return {"ok": False, "error": "File not found"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]
        return {"ok": True, "content": "".join(lines), "lines": len([l for l in lines if l])}
    except Exception as e: return {"ok": False, "error": str(e)}

def write_file(path, content):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        return {"ok": True, "path": path, "size": len(content)}
    except Exception as e: return {"ok": False, "error": str(e)}

def list_dir(path="."):
    try:
        entries = []
        for e in os.listdir(path):
            fp = os.path.join(path, e)
            entries.append({"name": e, "is_dir": os.path.isdir(fp), "size": os.path.getsize(fp) if os.path.isfile(fp) else 0})
        return {"ok": True, "entries": sorted(entries, key=lambda x: (not x["is_dir"], x["name"]))}
    except Exception as e: return {"ok": False, "error": str(e)}

def search_files(pattern, path="."):
    try:
        results = _glob.glob(os.path.join(path, "**", pattern), recursive=True)[:50]
        return {"ok": True, "matches": results}
    except Exception as e: return {"ok": False, "error": str(e)}

def fs_handle(action, **params):
    handlers = {
        "read_file": lambda: read_file(params.get("path", ""), params.get("max_lines", 200)),
        "write_file": lambda: write_file(params.get("path", ""), params.get("content", "")),
        "list_dir": lambda: list_dir(params.get("path", ".")),
        "search_files": lambda: search_files(params.get("pattern", "*"), params.get("path", ".")),
    }
    h = handlers.get(action)
    if not h: return {"ok": False, "error": f"Unknown action: {action}"}
    return h()
