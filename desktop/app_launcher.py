"""GBT Pro v2.1 - Desktop Launcher (standalone)"""
import sys,os,subprocess,time,threading

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0,BASE)

# Start Flask server
def run_server():
    from desktop_app import app
    app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False)

threading.Thread(target=run_server,daemon=True).start()
time.sleep(2)

# Start Nanobrowser
nb=os.path.join(os.path.dirname(BASE),"nanobrowser","nanobrowser.py")
if os.path.exists(nb):
    subprocess.Popen([sys.executable,nb],cwd=os.path.dirname(nb))
    print("Nanobrowser launched")
else:
    import webbrowser
    webbrowser.open("http://127.0.0.1:8765/dashboard")
    print("Opened in browser")

# Keep alive
try:
    while True:time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down")
