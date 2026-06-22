"""GBT Pro v2.1 - Desktop Launcher (no console)"""
import sys,os,subprocess,time,threading,json,urllib.request

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0,BASE)
sys.path.insert(0,os.path.join(BASE,"desktop"))

# Pre-import flask to verify it works
try:
    import flask
except Exception as e:
    import tkinter.messagebox as mb
    mb.showerror("GBT Pro","Flask not installed.\nRun: pip install flask psutil")
    sys.exit(1)

# Start server in background
def serve():
    from desktop_app import app
    app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False)

threading.Thread(target=serve,daemon=True).start()

# Wait for server
for _ in range(20):
    try:
        r=urllib.request.urlopen("http://127.0.0.1:8765/api/status",timeout=1)
        if r.status==200:break
    except:time.sleep(0.5)

# Launch nanobrowser (native tkinter app)
nano=os.path.join(os.path.dirname(BASE),"nanobrowser","nanobrowser.py")
if os.path.exists(nano):
    subprocess.Popen([sys.executable,nano],cwd=os.path.dirname(nano))
else:
    import webbrowser
    webbrowser.open("http://127.0.0.1:8765/dashboard")

# Keep alive
try:
    while True:time.sleep(1)
except KeyboardInterrupt:pass
