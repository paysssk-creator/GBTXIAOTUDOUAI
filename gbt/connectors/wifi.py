"""wifi.py — WiFi Analyzer connector (Windows)"""
import subprocess

def scan_networks():
    try: r = subprocess.run(["netsh","wlan","show","networks","mode=bssid"], shell=False, capture_output=True, text=True, timeout=15); return {"ok": True, "output": r.stdout[:3000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def interface_info():
    try: r = subprocess.run(["netsh","wlan","show","interfaces"], shell=False, capture_output=True, text=True, timeout=10); return {"ok": True, "output": r.stdout[:2000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def wifi_handle(action, **params):
    h = {"scan": scan_networks, "info": interface_info}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
