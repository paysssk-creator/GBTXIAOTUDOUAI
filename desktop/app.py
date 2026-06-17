"""GBT Desktop Agent v2.0 - Web/GUI"""
import os, sys, threading, platform as _plat
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.gbt_agent import GBTAgent
from tools.mcp_tools import register_all_mcp_tools
from gbt.mcp import get_mcp, call_mcp
from gbt.providers import PROVIDERS, AutoKeyConfig

class GBTDesktopApp:
    def __init__(self, provider="auto", project=None, web_mode=True):
        self.p = project or os.getcwd()
        try:
            import signal
            def _timeout_handler(signum, frame):
                raise TimeoutError("Agent init timeout")
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(15)  # 15 second timeout
            try:
                self.agent = GBTAgent(provider=provider, project_root=self.p)
                register_all_mcp_tools(self.agent._tools, self.p)
                print(f"GBT Agent [{self.agent.llm.provider_name}] ready")
            finally:
                signal.alarm(0)
        except Exception as e:
            print(f"Agent init: {e}")
            self.agent = None
            print("Demo mode - using mock data")
        self._launch_web()

    def _launch_web(self):
        try:
            from flask import Flask, request, jsonify, render_template_string
            app = Flask(__name__)
            @app.route("/")
            def home():
                tpl = os.path.join(os.path.dirname(__file__), "templates", "homepage.html")
                if os.path.exists(tpl):
                    with open(tpl, "r", encoding="utf-8") as f:
                        return render_template_string(f.read())
                return "<h1>GBT v2.0</h1><p>Homepage template not found.</p>"
            @app.route("/api/status")
            def api_status():
                mcp = get_mcp(); disc = AutoKeyConfig.scan()
                return jsonify({
                    "mcp_servers": mcp.list_servers(), "mcp_count": len(mcp.list_servers()),
                    "llm": self.agent.llm.provider_name if self.agent else "N/A",
                    "model": self.agent.llm.model if self.agent else "N/A",
                    "keys_available": sum(1 for v in disc.values() if v["status"]=="available"),
                    "keys_total": len(PROVIDERS),
                    "platform": _plat.system(), "python": _plat.python_version(),
                })
            @app.route("/api/providers")
            def api_providers():
                disc = AutoKeyConfig.scan(); r = {}
                for pid, info in disc.items():
                    r[pid] = {"name": info["config"]["name"], "status": info["status"]}
                return jsonify(r)
            @app.route("/api/chat", methods=["POST"])
            def api_chat():
                d = request.json or {}
                resp = self.agent.run(d.get("text",""))[:5000] if self.agent else "Agent not available"
                return jsonify({"response": resp})
            @app.route("/api/reason", methods=["POST"])
            def api_reason():
                d = request.json or {}
                if not self.agent: return jsonify({"error": "Agent not available"})
                rr = self.agent.deep_reason(d.get("text",""), d.get("mode","chain"))
                return jsonify({"mode":rr.mode.value,"conclusion":rr.conclusion,"confidence":rr.confidence})
            @app.route("/api/mcp")
            def api_mcp(): return jsonify({"servers": get_mcp().list_servers()})
            @app.route("/api/mcp/<s>", methods=["POST"])
            def api_mcp_call(s):
                rr = call_mcp(s)
                return jsonify({"ok":rr.ok,"data":rr.data[:3000],"error":rr.error})
            print("\n" + "="*50)
            print("  GBT v2.0 Web Homepage")
            print("  http://localhost:8765")
            print("="*50 + "\n")
            app.run(host="127.0.0.1", port=8765, debug=False)
        except ImportError:
            print("ERROR: pip install flask")

def main():
    import argparse
    p = argparse.ArgumentParser(description="GBT Desktop Agent v2.0")
    p.add_argument("--provider", default="auto"); p.add_argument("--project", default=os.getcwd())
    p.add_argument("--web", action="store_true")
    args = p.parse_args()
    GBTDesktopApp(provider=args.provider, project=args.project, web_mode=True)

if __name__ == "__main__":
    main()
