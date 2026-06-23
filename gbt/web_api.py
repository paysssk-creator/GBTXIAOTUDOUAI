"""
web_api.py — GBT 全能能力 Web API 服务 v1.0
监听 127.0.0.1:8765，把所有能力暴露给 nanobrowser 前端。
"""
import os, sys, json, logging
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 确保能力注册到路由器
import gbt.capabilities  # noqa: F401

from flask import Flask, request, jsonify, make_response

L = logging.getLogger("GBT.WebAPI")
app = Flask(__name__)

# 手动 CORS，避免依赖 flask_cors
@app.after_request
def after_request(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    resp.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    resp.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return resp

def ok(data=None, message=""):
    return {"ok": True, "data": data, "message": message, "time": datetime.now().isoformat()}

def fail(message, error="", code=400):
    return jsonify({"ok": False, "message": message, "error": error, "time": datetime.now().isoformat()}), code

# 延迟加载的全局对象
_ai_operator = None
_trader = None
_router_inited = False

def get_ai_operator():
    global _ai_operator
    if _ai_operator is None:
        from gbt.ai_operator import AIDeviceOperator
        _ai_operator = AIDeviceOperator(safe_mode=False)
    return _ai_operator

def get_trader():
    global _trader
    if _trader is None:
        from gbt.trader import AShareTrader
        _trader = AShareTrader()
    return _trader

def init_router_deps():
    """把 trader/brain/watcher/account 等依赖注入路由器"""
    global _router_inited
    if _router_inited:
        return
    from gbt.router import router
    trader = get_trader()
    router.set_dependency("trader", trader)
    router.set_dependency("desktop_ctl", get_ai_operator().desktop)
    try:
        from gbt.account import Account
        router.set_dependency("account", Account())
    except Exception as e:
        L.debug(f"Account 注入跳过: {e}")
    try:
        from gbt.brain import AutonomousBrain
        router.set_dependency("brain", AutonomousBrain(trader=trader))
    except Exception as e:
        L.debug(f"Brain 注入跳过: {e}")
    try:
        from gbt.watcher import NightWatcher
        router.set_dependency("watcher", NightWatcher())
    except Exception as e:
        L.debug(f"Watcher 注入跳过: {e}")
    _router_inited = True


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(ok({"status": "running", "version": "1.5.1"}))


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    try:
        llm_status = {}
        try:
            from gbt.providers import PROVIDERS
            for pid, cfg in PROVIDERS.items():
                key = os.environ.get(cfg.get("env", pid.upper() + "_API_KEY"), "")
                llm_status[pid] = {"name": cfg.get("name", pid), "has_key": bool(key)}
        except Exception as e:
            llm_status = {"error": str(e)}

        data = {
            "llm": llm_status,
            "trade": {"ready": True, "auto_trade": False, "watchlist_count": 40},
            "watcher": {"monitors": {"system": {"status": "ok"}}},
            "capabilities": 19,
            "modules": 42,
        }
        return jsonify(ok(data))
    except Exception as e:
        return fail("dashboard failed", str(e), 500)


@app.route("/api/market", methods=["GET"])
def market():
    try:
        trader = get_trader()
        watchlist = trader.WATCHLIST if hasattr(trader, "WATCHLIST") else {}
        codes = list(watchlist.keys())[:10]
        quotes = trader.fetch_quote(codes) if hasattr(trader, "fetch_quote") else {}
        result = []
        for code in codes:
            q = quotes.get(code, {})
            if hasattr(q, "__dict__"):
                q = q.__dict__
            result.append({
                "code": code,
                "name": watchlist.get(code, code),
                "price": q.get("price", 0),
                "change_pct": q.get("change_pct", q.get("pct_change", 0)),
            })
        return jsonify(ok(result))
    except Exception as e:
        return fail("market failed", str(e), 500)


@app.route("/api/capabilities", methods=["GET"])
def capabilities_list():
    try:
        from gbt.router import router
        caps = [c.to_dict() for c in router.capabilities.values()]
        return jsonify(ok(caps))
    except Exception as e:
        return fail("capabilities failed", str(e), 500)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", data.get("message", ""))
    if not text:
        return fail("缺少 text/message")
    try:
        init_router_deps()
        from gbt.router import router
        result = router.route(text)
        return jsonify(ok(_serialize_route_result(result)))
    except Exception as e:
        return fail("chat failed", str(e), 500)


def _serialize_route_result(result: Dict) -> Dict:
    """把 router.route 的结果转为可 JSON 序列化的字典"""
    import copy
    out = copy.deepcopy(result)
    cls = out.get("classification")
    if isinstance(cls, dict) and cls.get("capability") is not None:
        cap = cls["capability"]
        if hasattr(cap, "to_dict"):
            cls["capability"] = cap.to_dict()
    return out


@app.route("/api/desk/observe", methods=["POST"])
def desk_observe():
    try:
        op = get_ai_operator()
        result = op.observe()
        if result.get("ok") and "base64" in result:
            result["base64_preview"] = result["base64"][:200] + "..."
            del result["base64"]
        return jsonify(ok(result))
    except Exception as e:
        return fail("observe failed", str(e), 500)


@app.route("/api/desk/act", methods=["POST"])
def desk_act():
    data = request.get_json(force=True, silent=True) or {}
    action_type = data.get("action_type", data.get("action", ""))
    params = data.get("params", {})
    if not action_type:
        return fail("缺少 action_type")
    try:
        from gbt.ai_operator import DeviceAction
        op = get_ai_operator()
        action = DeviceAction(action_type=action_type, params=params, reasoning=data.get("reasoning", ""))
        result = op.act(action)
        return jsonify(ok(result))
    except Exception as e:
        return fail("act failed", str(e), 500)


@app.route("/api/desk/run_task", methods=["POST"])
def desk_run_task():
    data = request.get_json(force=True, silent=True) or {}
    task = data.get("task", "")
    max_steps = int(data.get("max_steps", 10))
    if not task:
        return fail("缺少 task")
    try:
        op = get_ai_operator()
        result = op.run_task(task, max_steps=max_steps)
        return jsonify(ok(result))
    except Exception as e:
        return fail("run_task failed", str(e), 500)



@app.route("/api/trade/analyze", methods=["POST"])
def trade_analyze():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "600519")
    try:
        from gbt.ai_operator import get_ai_operator
        op = get_ai_operator()
        b64 = op.ai_trader.capture()
        analysis = op.ai_trader.analyze_screen(b64, focus=code) if b64 else {"error": "无法截图"}
        return jsonify(ok(analysis))
    except Exception as e:
        return fail("trade analyze failed", str(e), 500)


@app.route("/api/trade/execute", methods=["POST"])
def trade_execute():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "600519")
    action = data.get("action", "buy")
    shares = int(data.get("shares", 100))
    try:
        op = get_ai_operator()
        result = op.trade_autonomous(code, action=action, shares=shares)
        return jsonify(ok(result))
    except Exception as e:
        return fail("trade execute failed", str(e), 500)


@app.route("/api/hacker/exec", methods=["POST"])
def hacker_exec():
    data = request.get_json(force=True, silent=True) or {}
    cmd = data.get("command", data.get("id", ""))
    action = data.get("action", "run")
    try:
        if action == "search" or "搜索" in cmd:
            from gbt.scraper import precision_lookup
            result = precision_lookup(cmd)
        elif action == "run" and cmd.strip().startswith(("python", "py")):
            result = {"mode": "code_exec", "status": "sandbox only", "command": cmd}
        else:
            result = {"mode": "hacker", "command": cmd, "action": action}
        return jsonify(ok(result))
    except Exception as e:
        return fail("hacker exec failed", str(e), 500)


@app.route("/api/mcp", methods=["POST"])
def mcp_call():
    data = request.get_json(force=True, silent=True) or {}
    server = data.get("server", "")
    method = data.get("method", "")
    try:
        from gbt.mcp import call_mcp
        result = call_mcp(server, method, data.get("params", {}))
        return jsonify(ok(result))
    except Exception as e:
        return fail("mcp failed", str(e), 500)


@app.route("/api/evolve", methods=["POST"])
def evolve():
    data = request.get_json(force=True, silent=True) or {}
    goal = data.get("goal", "优化项目")
    try:
        from gbt.evolve import run_evolve
        result = run_evolve(goal)
        return jsonify(ok(result))
    except Exception as e:
        return fail("evolve failed", str(e), 500)


@app.route("/api/guard", methods=["POST"])
def guard():
    try:
        from gbt.guard import scan_all
        result = scan_all(os.path.dirname(os.path.dirname(__file__)))
        return jsonify(ok(result))
    except Exception as e:
        return fail("guard failed", str(e), 500)


@app.route("/api/mirror", methods=["POST"])
def mirror():
    data = request.get_json(force=True, silent=True) or {}
    src = data.get("src", os.path.dirname(os.path.dirname(__file__)))
    try:
        from gbt.mirror import mirror_run
        result = mirror_run(src)
        return jsonify(ok(result))
    except Exception as e:
        return fail("mirror failed", str(e), 500)


@app.route("/api/watcher", methods=["GET"])
def watcher_status():
    try:
        from gbt.watcher import NightWatcher
        w = NightWatcher()
        result = w.get_status() if hasattr(w, "get_status") else {"status": "ok"}
        return jsonify(ok(result))
    except Exception as e:
        return fail("watcher failed", str(e), 500)


@app.route("/api/keys/import", methods=["POST"])
def keys_import():
    try:
        from gbt.keydb import auto_import
        auto_import()
        return jsonify(ok({}, "API keys 导入完成"))
    except Exception as e:
        return fail("keys import failed", str(e), 500)


def run_server(host="127.0.0.1", port=8765, debug=False):
    L.info(f"GBT Web API starting at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_server()
