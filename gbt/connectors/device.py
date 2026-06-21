"""device.py — Device connectors (Camera/Audio/Display/Process — Windows)"""
import subprocess, os

# ── Camera ──
def camera_snap():
    try:
        import tempfile; fp = os.path.join(tempfile.gettempdir(), "gbt_cam.jpg")
        ps = 'Add-Type -AssemblyName System.Drawing;[Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")|Out-Null;$cam=New-Object System.Windows.Forms.WebCamControl;$img=$cam.CaptureImage();$img.Save("'+fp+'")'
        subprocess.run(["powershell","-NoProfile","-Command",ps], shell=False, capture_output=True, timeout=15)
        return {"ok": True, "file": fp} if os.path.exists(fp) else {"ok": False, "error": "Capture failed"}
    except Exception as e: return {"ok": False, "error": str(e)}

def camera_list():
    try: r = subprocess.run(["powershell","-NoProfile","-Command","Get-PnpDevice -Class Camera|Select FriendlyName"], shell=False, capture_output=True, text=True, timeout=10); return {"ok": True, "cameras": [l.strip() for l in r.stdout.split("\n") if l.strip()][1:]}
    except Exception: return {"ok": True, "cameras": ["Default Camera"]}

# ── Audio ──
def audio_play(file=None):
    return {"ok": False, "error": "Use system default player"}
def audio_record(duration=5):
    return {"ok": False, "error": "Not implemented — requires microphone permissions"}
def audio_list():
    return {"ok": True, "devices": ["Default Speaker", "Default Microphone"]}

# ── Display ──
def display_screenshot():
    try: from PIL import ImageGrab; import io, base64; img = ImageGrab.grab(); buf = io.BytesIO(); img.save(buf, "PNG"); return {"ok": True, "data": base64.b64encode(buf.getvalue()).decode()}
    except ImportError: return {"ok": False, "error": "pillow not installed"}
    except Exception as e: return {"ok": False, "error": f"screenshot failed: {e}"}
def display_list():
    try: from screeninfo import get_monitors; return {"ok": True, "displays": [{"name": m.name, "width": m.width, "height": m.height} for m in get_monitors()]}
    except ImportError: return {"ok": True, "displays": [{"name": "Primary", "width": 1920, "height": 1080}]}
    except Exception as e: return {"ok": True, "displays": [{"name": "Primary", "width": 1920, "height": 1080}]}

# ── Process ──
def process_list():
    try: r = subprocess.run(["tasklist","/fo","csv","/nh"], shell=False, capture_output=True, text=True, timeout=10); procs = [{"name": l.split(",")[0].strip('"'), "pid": l.split(",")[1].strip('"')} for l in r.stdout.strip().split("\n")[:30] if l.strip() and len(l.split(","))>=2]; return {"ok": True, "processes": procs}
    except Exception as e: return {"ok": False, "error": str(e)}
def process_kill(pid):
    try: subprocess.run(["taskkill","/f","/pid",str(pid)], shell=False, capture_output=True, timeout=10); return {"ok": True, "killed": pid}
    except Exception as e: return {"ok": False, "error": str(e)}
def process_info(pid):
    try: r = subprocess.run(["tasklist","/fo","csv","/nh","/fi",f"PID eq {pid}"], shell=False, capture_output=True, text=True, timeout=10); return {"ok": True, "info": r.stdout[:1000]}
    except Exception as e: return {"ok": False, "error": str(e)}

def device_handle(device_type, action, **params):
    handlers = {
        "camera": {"snap": camera_snap, "list": camera_list},
        "audio": {"play": lambda: audio_play(params.get("file")), "record": lambda: audio_record(params.get("duration",5)), "list": audio_list},
        "display": {"screenshot": display_screenshot, "list": display_list},
        "process": {"list": process_list, "kill": lambda: process_kill(params.get("pid","")), "info": lambda: process_info(params.get("pid",""))},
    }
    dev = handlers.get(device_type, {})
    h = dev.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {device_type}.{action}"}
