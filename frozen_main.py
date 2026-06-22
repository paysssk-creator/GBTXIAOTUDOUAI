"""GBT Pro v2.1 — PyInstaller Frozen Entry Point
Replaces app_launcher.py for standalone .exe builds.
No .venv detection, no nanobrowser dependency.
Includes single-instance lock to prevent duplicate launches.
"""
import sys, os, time, threading, urllib.request, ctypes

# ── Single-instance lock (Windows named mutex) ──
MUTEX_NAME = "Local\\GBT_Pro_v2.1_SingleInstance"
kernel32 = ctypes.windll.kernel32
mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    import tkinter.messagebox as mb
    mb.showwarning("GBT Pro", "GBT Pro is already running!\nCheck your system tray or taskbar.")
    sys.exit(0)

# ── Determine base path (frozen or dev) ──
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "desktop"))

# ── Import desktop_app (triggers Flask + template loading) ──
try:
    from desktop_app import app
except Exception as e:
    import tkinter.messagebox as mb
    mb.showerror("GBT Pro", f"Failed to start GBT Pro:\n{e}")
    sys.exit(1)

# ── Start Flask server in background ──
def serve():
    app.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False)

threading.Thread(target=serve, daemon=True).start()

# ── Wait for server to be ready ──
for _ in range(30):
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=1)
        if r.status == 200:
            break
    except:
        time.sleep(0.5)

# ── Launch GUI window ──
try:
    import webview
    webview.create_window(
        "GBT Pro v2.1",
        "http://127.0.0.1:8765/dashboard",
        width=1280,
        height=800,
        min_size=(1000, 650),
    )
    webview.start()
except ImportError:
    import webbrowser
    webbrowser.open("http://127.0.0.1:8765/dashboard")
    print("pywebview not installed — opened in browser")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
