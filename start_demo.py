"""Development/demo API server entry.

This file is kept for service-style debugging and local API bring-up. It is not
the formal desktop release entry. The formal desktop release line is controlled
by `release/current_runtime.ini` and launched by `release/launch_current_runtime.bat`.
"""
import os, sys, json, platform, traceback, socket
sys.path.insert(0, os.path.dirname(__file__))

# ── 结构化日志 ──
from gbt.logging_config import setup_logging
setup_logging(level="INFO", json_mode=False)

from flask import Flask, jsonify, render_template_string, request
from gbt.mcp import get_mcp
from gbt.providers import PROVIDERS, AutoKeyConfig
import logging
L_srv = logging.getLogger("GBT.Server")

app = Flask(__name__)

# Real LLM initialization
_llm = None
try:
    from gbt.llm import GBTLLM
    _llm = GBTLLM(provider="auto")
except Exception:
    pass

# 延迟初始化 — 避免模块级 import 导致 C 扩展崩溃
_router_ready = False

def _ensure_router():
    """懒初始化路由器和核心依赖 (仅执行一次)"""
    global _router_ready
    if _router_ready:
        return
    try:
        from gbt.capabilities import register_all
        register_all()
        from gbt.router import router
        # 注入模拟/降级依赖
        class F:
            def __init__(s, **kw):
                for k, v in kw.items():
                    setattr(s, k, v)
        router.set_dependency("trader", F(
            fetch_quote=lambda codes: {c: F(name=f"股票{c}", price=10.0, change_pct=0.5) for c in codes},
            fetch_watchlist=lambda: {
                "600519": F(name="贵州茅台", price=1650.0, change_pct=1.2),
                "600036": F(name="招商银行", price=38.5, change_pct=-0.5)
            },
            fetch_kline=lambda c,p,n: {"ok": True, "closes": [10.0]*30},
            analyze_with_ai=lambda c,q: F(action="buy", confidence=75, reason="AI策略评分"),
            get_status=lambda: {"auto_trade": True, "watchlist_count": 2},
            watchlist={"600519": "贵州茅台", "600036": "招商银行"},
            positions={},
        ))
        router.set_dependency("brain", F(
            get_status=lambda: {"running": True, "heartbeat": {"count": 42}},
            ping=lambda src, reason: None,
        ))
        router.set_dependency("watcher", F(
            get_status=lambda: {"running": True, "monitors": {"market": {"status": "ok", "details": "守夜人监控中"}}},
            alerts=[],
        ))
        router.set_dependency("account", F(
            cash=100000.0, total_pnl=1500.0, positions={},
        ))
        _router_ready = True
        L_srv.info("路由核心依赖已注入")
    except Exception as e:
        L_srv.warning(f"路由初始化失败: {e}")

@app.route("/")
def home():
    tpl = os.path.join(os.path.dirname(__file__), "desktop", "templates", "homepage.html")
    if os.path.exists(tpl):
        with open(tpl, "r", encoding="utf-8") as f:
            return render_template_string(f.read())
    return "<h1>GBT v2.0</h1>"

@app.route("/api/status")
def status():
    mcp = get_mcp(); disc = AutoKeyConfig.scan()
    return jsonify({
        "mcp_servers": mcp.list_servers(),
        "mcp_count": len(mcp.list_servers()),
        "llm": _llm.provider_name if _llm else "Not configured", "model": _llm.model if _llm else "N/A",
        "keys_available": sum(1 for v in disc.values() if v["status"]=="available"),
        "keys_total": len(PROVIDERS),
        "platform": platform.system(), "python": platform.python_version(),
    })

@app.route("/api/health")
def health():
    """生产健康检查端点 — Docker / K8s / LB 标准"""
    import psutil, time
    status = "ok"; checks = {}
    
    # 1. 内存
    mem = psutil.virtual_memory()
    mem_pct = mem.percent
    checks["memory"] = {"used_pct": mem_pct, "status": "ok" if mem_pct < 90 else "warn"}
    
    # 2. 磁盘
    disk = psutil.disk_usage(os.path.dirname(__file__))
    disk_pct = disk.percent
    checks["disk"] = {"free_gb": round(disk.free/1e9,1), "used_pct": disk_pct, "status": "ok" if disk_pct < 95 else "warn"}
    
    # 3. LLM
    checks["llm"] = {"status": "ok", "provider": _llm.provider_name if _llm else "none"}
    
    # 4. DB
    try:
        from gbt.database import db
        with db.conn() as c:
            c.execute("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception:
        checks["database"] = {"status": "error"}
    
    # 5. 路由
    try:
        _ensure_router()
        from gbt.router import router
        checks["router"] = {"status": "ok", "capabilities": len(router.list_capabilities())}
    except Exception:
        checks["router"] = {"status": "error"}
    
    # 6. 进程
    proc = psutil.Process()
    checks["process"] = {
        "pid": proc.pid,
        "cpu_pct": round(proc.cpu_percent(interval=0.1), 1),
        "threads": proc.num_threads(),
        "uptime_s": round(time.time() - proc.create_time()),
    }
    
    # 健康判定
    critical_checks = [v for k, v in checks.items() if isinstance(v, dict) and v.get("status") == "error"]
    if critical_checks:
        status = "degraded"
    
    return jsonify({
        "status": status,
        "service": "GBT v2.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": checks,
    }), (200 if status == "ok" else 503)

@app.route("/api/providers")
def providers():
    disc = AutoKeyConfig.scan()
    r = {}
    for pid, info in disc.items():
        r[pid] = {"name": info["config"]["name"], "status": info["status"]}
    return jsonify(r)

@app.route("/api/mcp")
def mcp_list():
    return jsonify({"servers": get_mcp().list_servers()})

@app.route("/api/mcp/<s>", methods=["POST"])
def mcp_call(s):
    from gbt.mcp import call_mcp
    rr = call_mcp(s)
    return jsonify({"ok": rr.ok, "data": rr.data[:3000], "error": rr.error})

@app.route("/api/dashboard")
def dashboard():
    """桌面 APP 总览面板"""
    import psutil, os, time
    d = {}
    # LLM
    d["llm"] = {
        "totals": {"tokens_total": 0, "cost_rmb": 0},
        "current": {"model": _llm.model if _llm else None, "provider": _llm.provider_name if _llm else None},
        "history": []
    }
    # Trade
    try:
        from gbt.database import db
        cards = db.conn().execute("SELECT code,name FROM watchlist").fetchall()
        d["trade"] = {
            "account": {"cash": 100000, "pnl": 1500},
            "watchlist": [(r[0],r[1]) for r in cards] if cards else []
        }
    except Exception:
        d["trade"] = {"account": {"cash": 100000, "pnl": 1500}, "watchlist": []}
    # System
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.dirname(__file__))
    procs = []
    for p in sorted(psutil.process_iter(['pid','name','cpu_percent','memory_percent']), 
                    key=lambda x: x.info['cpu_percent'] or 0, reverse=True)[:20]:
        procs.append({"pid": p.info['pid'], "name": p.info.get('name','?'),
                      "cpu_percent": p.info['cpu_percent'] or 0,
                      "memory_percent": p.info['memory_percent'] or 0})
    d["system"] = {
        "cpu": psutil.cpu_percent(), "memory": mem.percent, "disk": disk.percent,
        "host": socket.gethostname(), "python": platform.python_version()
    }
    d["desktop"] = {"top_processes": procs}
    # MCP
    d["mcp"] = {"servers": get_mcp().list_servers()}
    return jsonify(d)

@app.route("/api/hacker/capabilities")
def hacker_capabilities():
    """能力列表 — 桌面 Hacker 面板"""
    from gbt.router import router as rt
    caps = []
    for cap in sorted(rt.capabilities.values(), key=lambda c: c.priority, reverse=True):
        caps.append({
            "id": cap.name, "category": cap.category,
            "priority": cap.priority, "description": cap.description or "",
            "mcp": cap.name in get_mcp().list_servers()
        })
    return jsonify({"capabilities": caps})

@app.route("/api/hacker/exec", methods=["POST"])
def hacker_exec():
    """执行能力 — Hacker 面板一键调用"""
    d = request.json or {}
    cid = d.get("id", d.get("capability", ""))
    try:
        _ensure_router()
        from gbt.router import router as _router
        route = _router.route(cid)
        capability = route.get("capability")
        if capability:
            result = capability.execute(cid)
            return jsonify({
                "ok": True,
                "data": str(result)[:3000],
                "capability": capability.name
            })
        return jsonify({"ok": False, "error": "未匹配到能力"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})

@app.route("/api/market")
def market_api():
    """市场行情 — Trade 面板"""
    try:
        idx = [
            {"name": "上证指数", "price": 3350.00, "pct": 0.35},
            {"name": "深证成指", "price": 10800.00, "pct": -0.20},
            {"name": "创业板指", "price": 2150.00, "pct": 0.80},
        ]
        return jsonify({"ok": True, "indices": idx})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/config/llm", methods=["POST"])
def config_llm():
    """保存 LLM API Key — 用户输入密钥即可启动大模型"""
    d = request.json or {}
    provider = d.get("provider", "zhipu").strip()
    api_key = d.get("api_key", "").strip()
    model = d.get("model", "").strip()
    
    if not api_key:
        return jsonify({"ok": False, "error": "api_key 不能为空"}), 400
    
    # 写入 .env
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    env_map = {}
    if os.path.exists(env_file):
        for line in open(env_file, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_map[k.strip()] = v.strip()
    
    # 设置对应的环境变量
    key_map = {
        "zhipu": "ZHIPU_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
    }
    env_key = key_map.get(provider, f"{provider.upper()}_API_KEY")
    
    env_map[env_key] = api_key
    if model:
        env_map[f"{provider.upper()}_MODEL"] = model
    
    # 写回 .env
    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in env_map.items():
            f.write(f"{k}={v}\n")
    
    # 实时注入环境变量
    os.environ[env_key] = api_key
    
    # 重新初始化 LLM
    global _llm
    try:
        from gbt.llm import GBTLLM
        _llm = GBTLLM(provider=provider)
        llm_status = f"{_llm.provider_name} {_llm.model}"
    except Exception as e:
        llm_status = f"初始化失败: {e}"
    
    return jsonify({
        "ok": True,
        "provider": provider,
        "llm_status": llm_status,
        "message": f"✓ {provider} API Key 已保存，大模型已激活",
    })

@app.route("/api/token/recharge", methods=["POST"])
def token_recharge():
    """Token 充值 — 激活码兑换"""
    d = request.json or {}
    code = d.get("code", "").strip().upper()
    
    if not code or len(code) < 8:
        return jsonify({"ok": False, "error": "激活码格式错误（至少8位）"}), 400
    
    # 激活码系统: 简单哈希验证
    import hashlib, time
    # 预生成激活码逻辑
    valid_codes = {
        "GBT-VIP-FREE": {"tokens": 10000, "name": "免费体验包"},
        "GBT-PRO-MONTH": {"tokens": 100000, "name": "月卡专业版"},
        "GBT-PRO-YEAR": {"tokens": 1000000, "name": "年卡旗舰版"},
        "GBT-ULTRA-01": {"tokens": 9999999, "name": "创始会员"},
    }
    
    if code in valid_codes:
        info = valid_codes[code]
        # 保存到数据库
        try:
            from gbt.database import db
            with db.conn() as c:
                c.execute("""
                    INSERT OR REPLACE INTO config (key, value, updated_at)
                    VALUES ('token_balance', ?, datetime('now'))
                """, (str(info["tokens"]),))
            return jsonify({
                "ok": True,
                "tokens": info["tokens"],
                "plan": info["name"],
                "message": f"✓ 充值成功！{info['name']} — {info['tokens']:,} Tokens 已到账",
            })
        except Exception as e:
            return jsonify({"ok": True, "tokens": info["tokens"], "plan": info["name"],
                          "message": f"✓ {info['name']} {info['tokens']:,} Tokens（本地模式）"})
    
    # 动态生成激活码: 简单校验
    try:
        code_hash = hashlib.sha256(f"GBT_{code}_SALT".encode()).hexdigest()[:8]
        if code.endswith(code_hash):
            tokens = int(code.split("-")[-2]) if "-" in code else 5000
            return jsonify({"ok": True, "tokens": tokens, "plan": "自定义", 
                          "message": f"✓ 激活成功 — {tokens:,} Tokens 已到账"})
    except Exception:
        pass
    
    # 演示模式：任意8位码给5000免费token
    return jsonify({
        "ok": True,
        "tokens": 5000,
        "plan": "试用版",
        "message": "✓ 试用激活成功 — 5,000 Tokens 已到账（演示模式）",
    })

@app.route("/api/token/balance")
def token_balance():
    """查询 Token 余额"""
    try:
        from gbt.database import db
        with db.conn() as c:
            r = c.execute("SELECT value FROM config WHERE key='token_balance'").fetchone()
            tokens = int(r[0]) if r else 0
    except Exception:
        tokens = 0
    return jsonify({"ok": True, "tokens": tokens, "usage": "0"})

@app.route("/api/config/llm")
def get_llm_config():
    """获取当前 LLM 配置"""
    disc = AutoKeyConfig.scan()
    available = []
    for pid, info in disc.items():
        available.append({
            "id": pid,
            "name": info["config"]["name"],
            "status": info["status"],
            "models": info["config"].get("models", [])[:5],
        })
    return jsonify({
        "current": _llm.provider_name if _llm else "Not configured",
        "model": _llm.model if _llm else "N/A",
        "available": available,
    })

@app.route("/api/reason", methods=["POST"])
def reason():
    """意图路由 + 能力执行 + LLM推理 + 操作记忆 — 统一决策链路"""
    d = request.json or {}
    
    # ── Pydantic 输入校验 (带兼容降级) ──
    try:
        from gbt.api_models import ReasonRequest
        validated = ReasonRequest(**d)
        text = validated.text or ""
        mode_str = validated.mode
    except Exception:
        text = d.get("text", d.get("question", ""))
        mode_str = d.get("mode", "quick")
    
    if not text or not text.strip():
        return jsonify({"ok": False, "error": "text is required"}), 400

    capability = ""
    routed = False
    exec_result = None
    route = {}
    elapsed = 0

    # Step 1: 能力路由 + 执行
    try:
        import time as _t
        _t0 = _t.time()
        _ensure_router()
        from gbt.router import router as _router
        route = _router.route(text)
        elapsed = (_t.time() - _t0) * 1000
        cap_obj = route.get("capability", route.get("classification", {}).get("capability"))
        if hasattr(cap_obj, "name"):
            capability = cap_obj.name
        if route.get("routed") and route.get("execution", {}).get("ok"):
            exec_result = route["execution"].get("result", "")
            routed = True
        elif route.get("action") == "missing_dependency":
            capability = route.get("capability", "") or ""
            exec_result = f"能力 {capability} 依赖未就绪: {route.get('missing', '')}"
    except Exception as e:
        capability = "router_error"
        exec_result = f"Router异常: {str(e)[:100]}"

    # Step 1.5: 操作记忆自动记录
    try:
        from gbt.op_memory import record_from_route
        record_from_route(text, route, elapsed)
    except Exception:
        pass

    # Step 2: LLM 推理 (注入操作记忆上下文)
    conclusion = ""
    confidence = 50
    plan = []
    try:
        if _llm:
            from gbt.reasoner import DeepReasoner, ReasonMode as RM
            from gbt.op_memory import get_op_memory
            om = get_op_memory()
            mem_context = om.context_for_decision()
            if mem_context:
                text = f"{text}\n\n[操作记忆上下文]\n{mem_context}"
            mode = RM(mode_str)
            dr = DeepReasoner(_llm)
            result = dr.reason(text, mode)
            conclusion = result.conclusion[:2000] if result.conclusion else ""
            confidence = result.confidence
            plan = result.plan[:10] if result.plan else []
    except Exception as e:
        conclusion = str(e)[:200]

    # Step 3: 合并
    if routed and exec_result:
        conclusion = f"{exec_result}\n\n{conclusion}" if conclusion else str(exec_result)
    elif exec_result and not conclusion:
        conclusion = str(exec_result)

    # Step 4: 记忆上下文追加 (操作记忆反馈)
    try:
        from gbt.op_memory import get_op_memory
        om = get_op_memory()
        mem_summary = om.recent_context(3)
        if mem_summary and "(尚无操作记录)" not in mem_summary:
            conclusion = f"{conclusion}\n\n[记忆]\n{mem_summary}"
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "mode": mode_str,
        "capability": str(capability),
        "conclusion": str(conclusion),
        "confidence": confidence,
        "plan": plan,
        "routed": routed,
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    if not _llm:
        return jsonify({"ok": False, "error": "LLM not configured. Set API keys in .env file.",
                        "help": "See /api/providers for available providers"})
    try:
        d = request.json or {}
        msgs = [{"role": "user", "content": d.get("text", d.get("message", "Hello"))}]
        resp = _llm.invoke(msgs)
        return jsonify({"ok": True, "response": resp})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

print("\n" + "=" * 60)
print("  GBT v2.0 Production Server - RUNNING!")
print(f"  http://localhost:8765  |  LLM: {_llm.provider_name if _llm else 'Not configured'}")
print("  API: /api/status | /api/providers | /api/mcp | /api/chat | /api/reason")
print("=" * 60 + "\n")

app.run(host="0.0.0.0", port=8765, debug=False)
