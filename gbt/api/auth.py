"""GBT Pro · gbt/api/auth.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：auth
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("auth", __name__)


@bp.route("/api/auth/register", methods=["POST"])
def auth_register():
    d = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "").strip()
    email = d.get("email", "").strip()
    from gbt.auth import get_auth
    ok, msg = get_auth().register(username, password, email)
    return jsonify({"ok": ok, "message": msg})


@bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    d = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "").strip()
    from gbt.auth import get_auth
    ok, msg, token = get_auth().login(username, password)
    return jsonify({"ok": ok, "message": msg, "token": token})


@bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    d = request.json or {}
    token = d.get("token", "")
    from gbt.auth import get_auth
    get_auth().logout(token)
    return jsonify({"ok": True, "message": "已退出"})


@bp.route("/api/auth/profile")
def auth_profile():
    token = request.args.get("token", "") or request.headers.get("X-Auth-Token", "")
    from gbt.auth import get_auth
    if not token:
        return jsonify({"ok": False, "error": "请先登录"}), 401
    username = get_auth().verify_session(token)
    if not username:
        return jsonify({"ok": False, "error": "会话过期，请重新登录"}), 401
    profile = get_auth().get_profile(username)
    return jsonify({"ok": True, "profile": profile})


@bp.route("/api/auth/oauth/providers")
def auth_oauth_providers():
    from gbt.auth import get_oauth
    return jsonify({"ok": True, "providers": get_oauth().provider_status()})


@bp.route("/api/auth/oauth/start/<provider>", methods=["POST"])
def auth_oauth_start(provider):
    from gbt.auth import get_oauth
    res = get_oauth().start(provider)
    if res.get("ok") and res.get("auth_url"):
        try:
            import webbrowser
            res["opened"] = bool(webbrowser.open(res["auth_url"]))
        except Exception:
            res["opened"] = False
    status = 200 if res.get("ok") else 503
    return jsonify(res), status


@bp.route("/api/auth/oauth/poll")
def auth_oauth_poll():
    state = request.args.get("state", "").strip()
    from gbt.auth import get_oauth
    res = get_oauth().poll(state)
    status = 200 if res.get("status") in ("pending", "success") else 400
    return jsonify(res), status


@bp.route("/api/auth/oauth/callback/<provider>")
def auth_oauth_callback(provider):
    state = request.args.get("state", "").strip()
    code = request.args.get("code", "").strip()
    error = request.args.get("error", "").strip()
    from gbt.auth import get_oauth
    res = get_oauth().finish(provider, state=state, code=code, error=error)
    title = "授权完成" if res.get("ok") else "授权失败"
    detail = (res.get("error") or "请回到 GBT Pro 桌面端，登录状态会自动刷新。").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{title}</title>
      <style>
        body{{font-family:Segoe UI,Arial,sans-serif;background:#0b1220;color:#e5eefc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
        .card{{width:min(560px,92vw);background:#111827;border:1px solid #334155;border-radius:16px;padding:28px;box-shadow:0 20px 50px rgba(0,0,0,.35)}}
        h1{{margin:0 0 12px;font-size:24px}}
        p{{line-height:1.7;color:#cbd5e1}}
        .ok{{color:#34d399}} .err{{color:#f87171}}
        .tip{{margin-top:16px;font-size:13px;color:#94a3b8}}
      </style>
    </head>
    <body>
      <div class="card">
        <h1 class="{'ok' if res.get('ok') else 'err'}">{title}</h1>
        <p>{detail}</p>
        <p class="tip">现在可以回到 GBT Pro 桌面端，系统会自动接管本次授权结果。</p>
      </div>
      <script>setTimeout(function(){{try{{window.close()}}catch(e){{}}}}, 1800);</script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__=="__main__":
    print("GBT Pro — AI驱动A股自主交易终端")
    threading.Thread(target=lambda:app.run(host="127.0.0.1",port=8765,debug=False,use_reloader=False,threaded=True),daemon=True).start()
    time.sleep(3)
    # 自主操盘自动启动
    try:
        from gbt.autopilot import get_pilot
        get_pilot().start()
    except Exception as e:
        print(f"[AUTOPILOT] Auto-start skipped: {e}")
    webview.create_window("GBT Pro — 自主操盘·AI智能交易终端","http://127.0.0.1:8765/dashboard",width=1280,height=800,min_size=(1000,650))
    webview.start()
