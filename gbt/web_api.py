"""
web_api.py 鈥?GBT 鍏ㄨ兘鑳藉姏 Web API 鏈嶅姟 v1.0
鐩戝惉 127.0.0.1:8765锛屾妸鎵€鏈夎兘鍔涙毚闇茬粰 nanobrowser 鍓嶇銆?
"""
import os, sys, json, logging
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 纭繚鑳藉姏娉ㄥ唽鍒拌矾鐢卞櫒
import gbt.capabilities  # noqa: F401

from flask import Flask, request, jsonify, make_response

L = logging.getLogger("GBT.WebAPI")
app = Flask(__name__)

# 鎵嬪姩 CORS锛岄伩鍏嶄緷璧?flask_cors
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

# 寤惰繜鍔犺浇鐨勫叏灞€瀵硅薄
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
    """鎶?trader/brain/watcher/account 绛変緷璧栨敞鍏ヨ矾鐢卞櫒"""
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
        L.debug(f"Account 娉ㄥ叆璺宠繃: {e}")
    try:
        from gbt.brain import AutonomousBrain
        router.set_dependency("brain", AutonomousBrain(trader=trader))
    except Exception as e:
        L.debug(f"Brain 娉ㄥ叆璺宠繃: {e}")
    try:
        from gbt.watcher import NightWatcher
        router.set_dependency("watcher", NightWatcher())
    except Exception as e:
        L.debug(f"Watcher 娉ㄥ叆璺宠繃: {e}")
    _router_inited = True


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(ok({"status": "running", "version": "v4.0.7"}))



@app.route('/')
def dashboard_html():
    try:
        p = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        if os.path.exists(p):
            return open(p, 'r', encoding='utf-8').read()
        return '<h1>GBT AI Workstation v4</h1><p>Open http://127.0.0.1:8765/api/health</p>'
    except Exception as e:
        return f'<h1>Error</h1><p>{e}</p>'

@app.route("/api/dashboard", methods=["GET"])
def dashboard_api():

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
        return fail("缂哄皯 text/message")
    try:
        init_router_deps()
        from gbt.router import router
        result = router.route(text)
        return jsonify(ok(_serialize_route_result(result)))
    except Exception as e:
        return fail("chat failed", str(e), 500)


def _serialize_route_result(result: Dict) -> Dict:
    """鎶?router.route 鐨勭粨鏋滆浆涓哄彲 JSON 搴忓垪鍖栫殑瀛楀吀"""
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
        return fail("缂哄皯 action_type")
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
        return fail("缂哄皯 task")
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
        analysis = op.ai_trader.analyze_screen(b64, focus=code) if b64 else {"error": "鏃犳硶鎴浘"}
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
        if cmd == "screen_ocr":
            op = get_ai_operator()
            result = op.observe(use_llm=False)
            return jsonify(ok(result))
        if cmd == "screen_ai":
            op = get_ai_operator()
            result = op.observe(use_llm=True)
            return jsonify(ok(result))
        if action == "search" or "鎼滅储" in cmd:
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
    goal = data.get("goal", "浼樺寲椤圭洰")
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
        return jsonify(ok({}, "API keys 瀵煎叆瀹屾垚"))
    except Exception as e:
        return fail("keys import failed", str(e), 500)


@app.route("/api/nanobrowser/start", methods=["POST"])
def nb_start():
    from gbt.adapters import nanobrowser
    return jsonify(ok(nanobrowser.start()))

@app.route("/api/nanobrowser/stop", methods=["POST"])
def nb_stop():
    from gbt.adapters import nanobrowser
    return jsonify(ok(nanobrowser.stop()))

@app.route("/api/nanobrowser/status", methods=["GET"])
def nb_status():
    from gbt.adapters import nanobrowser
    return jsonify(ok(nanobrowser.status()))

@app.route("/api/cradle/run", methods=["POST"])
def cradle_run():
    from gbt.adapters import cradle
    from gbt.task_engine import TaskEngine
    data = request.get_json(force=True, silent=True) or {}
    task = data.get("task", "")
    env_config = data.get("env_config", "")
    result = cradle.run_task(task=task, env_config=env_config)
    if not result.get("ok"):
        engine = TaskEngine(max_steps=data.get("max_steps", 5), safe_mode=False)
        result = engine.run(task)
        result["source"] = "task_engine_fallback"
    else:
        result["source"] = "cradle"
    return jsonify(ok(result))

@app.route("/api/cradle/status", methods=["GET"])
def cradle_status():
    from gbt.adapters import cradle
    return jsonify(ok(cradle.status()))

@app.route("/api/screenpipe/start", methods=["POST"])
def screenpipe_start():
    from gbt.adapters import screenpipe
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(ok(screenpipe.start(mode=data.get("mode", "screen"), interval=data.get("interval", 2.0))))

@app.route("/api/screenpipe/stop", methods=["POST"])
def screenpipe_stop():
    from gbt.adapters import screenpipe
    return jsonify(ok(screenpipe.stop()))

@app.route("/api/screenpipe/status", methods=["GET"])
def screenpipe_status():
    from gbt.adapters import screenpipe
    return jsonify(ok(screenpipe.status()))

@app.route("/api/screenpipe/recent", methods=["GET"])
def screenpipe_recent():
    from gbt.adapters import screenpipe
    limit = request.args.get("limit", 10, type=int)
    return jsonify(ok(screenpipe.recent(limit=limit)))


def run_server(host="127.0.0.1", port=8765, debug=False):
    L.info(f"GBT Web API starting at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_server()
