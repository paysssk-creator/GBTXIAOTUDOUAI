"""network.py — Network Scanner connector"""
import os, subprocess, shlex

def ping_host(host, count=4):
    try: r = subprocess.run(["ping", "-n", str(count), str(host)], shell=False, capture_output=True, text=True, timeout=15); return {"ok": r.returncode == 0, "output": r.stdout[:2000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def dns_lookup(host):
    try: r = subprocess.run(["nslookup", str(host)], shell=False, capture_output=True, text=True, timeout=10); return {"ok": r.returncode == 0, "output": r.stdout[:2000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def traceroute(host):
    try: r = subprocess.run(["tracert", "-h", "10", str(host)], shell=False, capture_output=True, text=True, timeout=60); return {"ok": True, "output": r.stdout[:3000]}
    except Exception as e: return {"ok": False, "error": str(e)}

_DEFAULT_PING = os.getenv("PING_TARGET", "8.8.8.8")
_DEFAULT_DNS = "google.com"

def net_handle(action, **params):
    h = {"ping": lambda: ping_host(params.get("host", _DEFAULT_PING), params.get("count", 4)),
         "dns": lambda: dns_lookup(params.get("host", _DEFAULT_DNS)),
         "traceroute": lambda: traceroute(params.get("host", _DEFAULT_PING))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
