"""GBT Pro Server — Flask only (no GUI). Use for production/testing."""
import sys, os, time, threading

sys.path.insert(0, os.path.dirname(__file__))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from desktop_app import app

if __name__ == "__main__":
    print("GBT Pro Server starting on 127.0.0.1:8765")
    # 自主操盘自动启动
    try:
        from gbt.autopilot import get_pilot
        get_pilot().start()
        print("[AUTOPILOT] Started")
    except Exception as e:
        print(f"[AUTOPILOT] Auto-start skipped: {e}")
    app.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False, threaded=True)
