"""registry.py — Windows Registry connector"""
import subprocess

def read_key(key):
    try: r = subprocess.run(["reg","query",key], shell=False, capture_output=True, text=True, timeout=10); return {"ok": r.returncode == 0, "output": r.stdout[:3000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def write_key(key, value_name, value, reg_type="REG_SZ"):
    try: r = subprocess.run(["reg","add",key,"/v",value_name,"/t",reg_type,"/d",value,"/f"], shell=False, capture_output=True, text=True, timeout=10); return {"ok": r.returncode == 0, "output": r.stdout[:1000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def reg_handle(action, **params):
    h = {"read": lambda: read_key(params.get("key","")), "write": lambda: write_key(params.get("key",""), params.get("value_name",""), params.get("value",""))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
