import sys,os,ctypes,threading,time
if getattr(sys,'frozen',False):
    d=os.path.dirname(sys.executable)
else:
    d=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(d)
# Load .env
ep=os.path.join(d,'.env')
if os.path.exists(ep):
    from dotenv import load_dotenv;load_dotenv(ep)
sys.path.insert(0,d)
from gbt.desktop_app import run_app
run_app()