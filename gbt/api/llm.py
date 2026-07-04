"""GBT Pro · gbt/api/llm.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：llm
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time, re
import urllib.request, urllib.error
from pathlib import Path
bp = Blueprint("llm", __name__)


KEY_MAP = {
    "zhipu": "ZHIPU_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "hunyuan": "HUNYUAN_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "grok": "GROK_API_KEY",
    "doubao": "DOUBAO_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "stepfun": "STEPFUN_API_KEY",
    "openclaw": "OPENCLAW_API_KEY",
}


def _device_store_dir() -> Path:
    base = (
        os.environ.get("GBT_DEVICE_DATA_DIR", "").strip()
        or os.environ.get("LOCALAPPDATA", "").strip()
        or os.environ.get("APPDATA", "").strip()
        or str(Path.home())
    )
    path = Path(base) / "GBTPro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _legacy_env_file() -> Path:
    return Path(__file__).resolve().parent / ".env"


def _device_env_file() -> Path:
    return _device_store_dir() / "llm_device.env"


def _device_cfg_file() -> Path:
    return _device_store_dir() / "llm_device.json"


def _read_env_file(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _write_env_file(path: Path, env_map: dict):
    lines = [f"{k}={v}" for k, v in env_map.items() if str(v).strip() != ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _load_saved_llm_env():
    merged = {}
    for path in (_legacy_env_file(), _device_env_file()):
        merged.update(_read_env_file(path))
    for key, value in merged.items():
        if value:
            os.environ[key] = value
    return merged


def _read_device_cfg() -> dict:
    path = _device_cfg_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_device_cfg(cfg: dict):
    path = _device_cfg_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _mask_key(raw: str) -> str:
    raw = str(raw or "").strip()
    if len(raw) <= 8:
        return "*" * len(raw) if raw else ""
    return raw[:6] + "*" * max(4, len(raw) - 10) + raw[-4:]


def _bootstrap_device_cfg_from_env():
    saved = _read_device_cfg()
    if saved.get("provider"):
        return saved
    try:
        from gbt.providers import detect_keys, PROVIDERS
        discovered = detect_keys()
        preferred = None
        if discovered.get("deepseek", {}).get("status") == "available":
            preferred = "deepseek"
        else:
            ranked = []
            for pid, info in discovered.items():
                if info.get("status") != "available":
                    continue
                ranked.append((int(PROVIDERS.get(pid, {}).get("tier", 999)), pid, info))
            ranked.sort(key=lambda item: item[0])
            preferred = ranked[0][1] if ranked else None
        if not preferred:
            return saved
        env_key = KEY_MAP.get(preferred, f"{preferred.upper()}_API_KEY")
        api_key = os.environ.get(env_key, "").strip()
        if not api_key:
            return saved
        cfg = {
            "provider": preferred,
            "model": os.environ.get(f"{preferred.upper()}_MODEL", "").strip(),
            "env_key": env_key,
            "saved_at": int(time.time()),
            "key_masked": _mask_key(api_key),
        }
        _write_device_cfg(cfg)
        return cfg
    except Exception:
        return saved


def _resolve_saved_provider_cfg(provider: str = ""):
    _load_saved_llm_env()
    device_cfg = _bootstrap_device_cfg_from_env()
    selected = (provider or device_cfg.get("provider") or "").strip().lower()
    if not selected:
        return None, None, device_cfg
    env_key = KEY_MAP.get(selected, f"{selected.upper()}_API_KEY")
    api_key = os.environ.get(env_key, "").strip()
    model = str(device_cfg.get("model", "") or "").strip()
    if not api_key:
        return None, model, device_cfg
    return {"provider": selected, "env_key": env_key, "api_key": api_key}, model, device_cfg


def _cloud_brain_cfg_file() -> Path:
    return _device_store_dir() / "cloud_brain.json"


def _read_cloud_brain_cfg() -> dict:
    path = _cloud_brain_cfg_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_cloud_brain_cfg(cfg: dict):
    path = _cloud_brain_cfg_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_cloud_mode(raw: str = "") -> str:
    raw = str(raw or "").strip().lower()
    if raw in {"cloud", "cloud_only"}:
        return "cloud"
    if raw in {"cloud_preferred", "hybrid", "auto"}:
        return "cloud_preferred"
    return "local"


def _default_cloud_brain_url() -> str:
    return (
        os.environ.get("GBT_CLOUD_BRAIN_URL", "").strip()
        or "https://gbtxiaotudouv1-gbt-cloud-brain.hf.space"
    )


def _cloud_brain_runtime_cfg() -> dict:
    saved = _read_cloud_brain_cfg()
    url = str(saved.get("url") or _default_cloud_brain_url()).strip().rstrip("/")
    mode = _normalize_cloud_mode(saved.get("chat_mode", "local"))
    timeout_sec = int(saved.get("timeout_sec", 45) or 45)
    enabled = bool(saved.get("enabled")) and bool(url)
    return {
        "url": url,
        "enabled": enabled,
        "chat_mode": mode,
        "timeout_sec": min(max(timeout_sec, 5), 120),
        "saved_on_device": bool(saved),
        "updated_at": saved.get("updated_at"),
    }


def _probe_cloud_brain(url: str, timeout_sec: int = 8) -> dict:
    url = str(url or "").strip().rstrip("/")
    if not url:
        return {"ok": False, "error": "cloud brain url 不能为空"}
    req = urllib.request.Request(url + "/api/status", headers={"User-Agent": "GBTPro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(body or "{}")
        return {
            "ok": bool(data.get("ok")),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "role": data.get("role"),
            "release_tag": data.get("release_tag"),
            "status_code": 200,
        }
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def _call_cloud_brain(path: str, payload: dict, timeout_sec: int = 45) -> dict:
    cfg = _cloud_brain_runtime_cfg()
    if not cfg.get("enabled") or not cfg.get("url"):
        return {"ok": False, "error": "云端大脑未启用"}
    raw = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        cfg["url"] + path,
        data=raw,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "GBTPro/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout_sec or cfg["timeout_sec"]) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
    data = json.loads(body or "{}")
    if not isinstance(data, dict):
        return {"ok": False, "error": "云端返回格式无效"}
    return data


def _estimate_cloud_metrics(text: str, content: str, model: str) -> dict:
    tokens_in = max(1, int(len(text or "") / 2))
    tokens_out = max(1, int(len(content or "") / 2))
    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_rmb": 0,
        "time": time.strftime("%H:%M:%S"),
        "model": model or "cloud-brain",
    }


_load_saved_llm_env()


def _is_capability_scope_query(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    return bool(re.search(
        r"操控电脑|操作电脑|控制电脑|能做什么|有什么能力|达到什么程度|支持哪些|会不会操作|桌面能力|电脑能力",
        text,
        re.I,
    ))


def _capability_snapshot():
    items = []
    try:
        from gbt.router import router as rt
        from gbt.capabilities import register_all
        register_all()
        for cap in sorted(rt.capabilities.values(), key=lambda c: c.priority, reverse=True):
            items.append({
                "id": cap.name,
                "name": cap.description or cap.name,
                "cat": cap.category or "core",
                "priority": int(getattr(cap, "priority", 0) or 0),
                "keywords": list((cap.keywords or [])[:3]),
            })
    except Exception:
        items = []
    return items


def _capability_scope_answer() -> str:
    caps = _capability_snapshot()
    total = len(caps)
    direct = [c for c in caps if c["id"] in {
        "gcc_run", "browser_open", "window_maximize", "screenshot",
        "keyboard_type", "keyboard_hotkey", "mouse_click", "mouse_move",
        "window_focus", "process_list", "process_kill", "system_lock",
    }]
    trade = [c for c in caps if c["id"] in {
        "market_scan", "stock_lookup", "account_query", "auto_trade",
    }]
    top_direct = "、".join(c["name"] for c in direct[:8]) or "浏览器、窗口、截图、键盘鼠标、进程查询"
    top_trade = "、".join(c["name"] for c in trade[:4]) or "行情扫描、个股分析、账户查询、自主操盘"
    stack_line = ""
    try:
        from gbt.control_stack import build_control_stack_report
        stack_report = build_control_stack_report()
        stack_summary = stack_report.get("summary", {})
        total_stacks = int(stack_summary.get("total_external_stacks", 0) or 0)
        ready_stacks = int(stack_summary.get("snapshot_ready_external_stacks", 0) or 0)
        if total_stacks:
            stack_line = (
                f"\n4. 外部操控栈：已锁定 {total_stacks} 套第三方电脑使用框架快照，"
                f"当前本机已就绪 {ready_stacks} 套；默认仍以原生桌面操控链为主，避免影响当前操盘稳定性。"
            )
    except Exception:
        stack_line = ""
    return (
        f"当前这套桌面运行时核心就两件事：电脑操控和自主操盘。我这边已经接上本机能力，共识别到 {total or '多项'} 项可用能力。\n\n"
        f"1. 电脑直接操作：{top_direct}。\n"
        f"2. 交易操盘能力：{top_trade}。\n"
        "3. 实际可落地动作包括屏幕截图、窗口切换、快捷键输入、进程检查、桌面状态读取，以及围绕看盘与执行的辅助操作。\n\n"
        "边界说明：高风险动作不会默认乱执行，像终止进程、锁屏、下单这类操作需要你明确确认；"
        "普通查询、能力说明和低风险引导可以直接给你结果。"
        f"{stack_line}"
    )


@bp.route("/api/config/llm", methods=["POST"])
def config_llm():
    """保存并初始化 LLM — 用户输入密钥即可启动大模型"""
    d = request.json or {}
    provider = d.get("provider", "zhipu").strip()
    api_key = d.get("api_key", "").strip()
    model = d.get("model", "").strip()
    provider = provider.lower() or "zhipu"
    env_key = KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")

    if not api_key:
        saved, saved_model, _ = _resolve_saved_provider_cfg(provider)
        if not saved:
            return jsonify({"ok": False, "error": "api_key 不能为空，且本机尚未保存该提供商密钥"}), 400
        api_key = saved["api_key"]
        if not model:
            model = saved_model or ""

    device_env = _read_env_file(_device_env_file())
    legacy_env = _read_env_file(_legacy_env_file())
    device_env[env_key] = api_key
    legacy_env[env_key] = api_key
    if model:
        device_env[f"{provider.upper()}_MODEL"] = model
        legacy_env[f"{provider.upper()}_MODEL"] = model
    _write_env_file(_device_env_file(), device_env)
    _write_env_file(_legacy_env_file(), legacy_env)
    _write_device_cfg({
        "provider": provider,
        "model": model,
        "env_key": env_key,
        "saved_at": int(time.time()),
        "key_masked": _mask_key(api_key),
    })

    os.environ[env_key] = api_key
    if model:
        os.environ[f"{provider.upper()}_MODEL"] = model

    # 测试连接
    conn_msg = ""
    conn_ok = False
    try:
        from gbt.llm import GBTLLM
        llm = GBTLLM(provider=provider, api_key=api_key, timeout=10)
        # 只试一次，不重试
        resp = llm._client.chat.completions.create(
            model=llm.model,
            messages=[{"role": "user", "content": "hi"}],
            temperature=0, max_tokens=10, stream=False)
        content = (resp.choices[0].message.content or "") if resp.choices else ""
        llm_name = llm.provider_name
        llm_model = llm.model
        conn_ok = True
        conn_msg = f"已连接 {llm_name} {llm_model}"
    except Exception as e:
        err = str(e)
        if "401" in err or "Unauthorized" in err or "Invalid" in err or "key" in err.lower():
            conn_msg = "Key无效 — 请检查API Key是否正确（Key已保存）"
        elif "404" in err or "not found" in err.lower():
            conn_msg = "模型不可用 — 请检查模型名称（Key已保存）"
        elif "timeout" in err.lower() or "connect" in err.lower():
            conn_msg = "网络超时 — 请检查网络连接（Key已保存）"
        elif "Rate" in err or "quota" in err.lower():
            conn_msg = "额度不足 — 请更换可用Key（Key已保存）"
        else:
            conn_msg = f"Key已保存，连接测试失败: {err[:60]}"

    return jsonify({
        "ok": conn_ok,
        "provider": provider,
        "message": conn_msg,
        "llm_name": conn_msg,
        "saved_on_device": True,
        "key_masked": _mask_key(api_key),
        "model": model or None,
    })


@bp.route("/api/config/cloud_brain", methods=["POST"])
def config_cloud_brain():
    d = request.json or {}
    url = str(d.get("url") or _default_cloud_brain_url()).strip().rstrip("/")
    enabled = bool(d.get("enabled", True))
    mode = _normalize_cloud_mode(d.get("chat_mode", "cloud_preferred"))
    timeout_sec = int(d.get("timeout_sec", 45) or 45)
    if enabled:
        probe = _probe_cloud_brain(url, timeout_sec=min(timeout_sec, 12))
        if not probe.get("ok"):
            return jsonify({
                "ok": False,
                "error": "云端大脑连通性检查失败: " + (probe.get("error") or "未知错误"),
                "url": url,
            }), 400
    cfg = {
        "url": url,
        "enabled": enabled,
        "chat_mode": mode,
        "timeout_sec": min(max(timeout_sec, 5), 120),
        "updated_at": int(time.time()),
    }
    _write_cloud_brain_cfg(cfg)
    os.environ["GBT_CLOUD_BRAIN_URL"] = url
    return jsonify({
        "ok": True,
        "saved_on_device": True,
        "url": url,
        "enabled": enabled,
        "chat_mode": mode,
        "timeout_sec": cfg["timeout_sec"],
        "status": _probe_cloud_brain(url, timeout_sec=min(cfg["timeout_sec"], 12)) if enabled else {"ok": False, "error": "disabled"},
    })


@bp.route("/api/config/cloud_brain")
def get_cloud_brain_config():
    cfg = _cloud_brain_runtime_cfg()
    status = _probe_cloud_brain(cfg["url"], timeout_sec=min(cfg["timeout_sec"], 8)) if cfg.get("enabled") else {"ok": False, "error": "disabled"}
    return jsonify({
        "ok": True,
        **cfg,
        "status": status,
    })


@bp.route("/api/cloud_brain/chat", methods=["POST"])
def cloud_brain_chat():
    d = request.json or {}
    txt = str(d.get("text", "")).strip()
    if not txt:
        return jsonify({"ok": False, "error": "text 不能为空"}), 400
    try:
        data = _call_cloud_brain("/api/chat", {"text": txt})
        return jsonify({
            "ok": bool(data.get("ok")),
            "response": data.get("response"),
            "provider": data.get("provider") or "GBT Cloud Brain",
            "model": data.get("model") or "cloud-brain",
            "brain_mode": "cloud",
            "error": data.get("error"),
        }), (200 if data.get("ok") else 502)
    except Exception as e:
        return jsonify({"ok": False, "error": f"云端大脑调用失败: {str(e)[:150]}"}), 502


@bp.route("/api/cloud_brain/plan", methods=["POST"])
def cloud_brain_plan():
    d = request.json or {}
    objective = str(d.get("objective", "")).strip()
    context = str(d.get("context", "")).strip()
    if not objective:
        return jsonify({"ok": False, "error": "objective 不能为空"}), 400
    try:
        data = _call_cloud_brain("/api/plan", {"objective": objective, "context": context})
        return jsonify({
            "ok": bool(data.get("ok")),
            "plan": data.get("plan"),
            "provider": data.get("provider") or "GBT Cloud Brain",
            "model": data.get("model") or "cloud-brain",
            "brain_mode": "cloud",
            "error": data.get("error"),
        }), (200 if data.get("ok") else 502)
    except Exception as e:
        return jsonify({"ok": False, "error": f"云端大脑计划生成失败: {str(e)[:150]}"}), 502


@bp.route("/api/chat", methods=["POST"])
def api_chat():
    """LLM 对话 — DeepSeek-reasoner 深度推理 / 常规chat双模式"""
    d = request.json or {}
    txt = d.get("text", "").strip()
    deep = d.get("deep_reasoning", False)  # True=使用推理大模型
    if not txt:
        return jsonify({"ok": False, "error": "输入为空"})
    llm_metrics = {"tokens_in": 0, "tokens_out": 0, "cost_rmb": 0, "time": time.strftime("%H:%M:%S"), "model": "none"}
    if _is_capability_scope_query(txt):
        remaining = None
        auth_token = d.get("token", "").strip() or request.headers.get("X-Auth-Token", "").strip()
        try:
            from gbt.auth import get_auth, get_balance
            user_id = "_default"
            if auth_token:
                verified = get_auth().verify_session(auth_token)
                if verified:
                    user_id = verified
            bal = get_balance().get_balance(user_id)
            remaining = max(0, int(bal.get("tokens", 0)) - int(bal.get("used", 0)))
        except Exception:
            remaining = None
        return jsonify({
            "ok": True,
            "response": _capability_scope_answer(),
            "reasoning": None,
            "model": "capability-registry",
            "provider": "GBT Runtime",
            "deep_reasoning": False,
            "metrics": llm_metrics,
            "tokens_consumed": 0,
            "tokens_remaining": remaining,
        })
    try:
        _load_saved_llm_env()
        from gbt.providers import detect_keys, PROVIDERS
        discovered = detect_keys()
        provider = None
        api_key = None
        # DeepSeek优先
        if "deepseek" in discovered and discovered["deepseek"]["status"] == "available":
            provider = "deepseek"
            ds_keys = discovered["deepseek"].get("found_keys", [])
            api_key = ds_keys[0].get("raw", "") if ds_keys else os.environ.get("DEEPSEEK_API_KEY", "")
        else:
            for pid, info in discovered.items():
                found_keys = info.get("found_keys", [])
                if info["status"] == "available" and found_keys:
                    provider = pid
                    api_key = found_keys[0].get("raw", "")
                    break
        if not provider:
            return jsonify({"ok": False, "error": "未找到可用LLM Key，请先在「连接大模型」面板配置API Key后重试"})
        # 可选鉴权：前端未登录时走默认余额；登录后可通过 token 绑定到个人余额
        user_id = "_default"
        auth_token = d.get("token", "").strip() or request.headers.get("X-Auth-Token", "").strip()
        try:
            from gbt.auth import get_auth, get_balance
            if auth_token:
                verified = get_auth().verify_session(auth_token)
                if not verified:
                    return jsonify({"ok": False, "error": "会话过期，请重新登录"}), 401
                user_id = verified
            balance = get_balance().get_balance(user_id)
            remaining = max(0, int(balance.get("tokens", 0)) - int(balance.get("used", 0)))
            if remaining <= 0:
                if user_id == "_default":
                    return jsonify({
                        "ok": False,
                        "error": "当前为访客模式，Token余额为0。请先登录领取新用户10000 tokens 后再开始对话。当前版本已移除付费模块。"
                    }), 402
                return jsonify({"ok": False, "error": "Token余额不足。当前版本已移除付费模块，请专注使用电脑操控与自主操盘主能力。"}), 402
        except Exception:
            remaining = None
        cloud_cfg = _cloud_brain_runtime_cfg()
        requested_mode = _normalize_cloud_mode(d.get("brain_mode", "") or cloud_cfg.get("chat_mode", "local"))
        if requested_mode in {"cloud", "cloud_preferred"} and cloud_cfg.get("enabled") and cloud_cfg.get("url"):
            try:
                cloud_data = _call_cloud_brain("/api/chat", {"text": txt}, timeout_sec=cloud_cfg.get("timeout_sec", 45))
                if cloud_data.get("ok"):
                    cloud_text = str(cloud_data.get("response", "") or "")
                    llm_metrics = _estimate_cloud_metrics(txt, cloud_text, cloud_data.get("model") or "cloud-brain")
                    consumed = max(1, int(llm_metrics["tokens_in"]) + int(llm_metrics["tokens_out"]))
                    try:
                        from gbt.auth import get_balance
                        if not get_balance().consume(user_id, consumed):
                            if user_id == "_default":
                                return jsonify({
                                    "ok": False,
                                    "error": "当前为访客模式，Token余额为0。请先登录领取新用户10000 tokens 后再开始对话。当前版本已移除付费模块。"
                                }), 402
                            return jsonify({"ok": False, "error": "Token余额不足。当前版本已移除付费模块，请专注使用电脑操控与自主操盘主能力。"}), 402
                        bal = get_balance().get_balance(user_id)
                        remaining = max(0, int(bal.get("tokens", 0)) - int(bal.get("used", 0)))
                    except Exception:
                        remaining = None
                    return jsonify({
                        "ok": True,
                        "response": cloud_text[:6000],
                        "reasoning": None,
                        "model": cloud_data.get("model") or "cloud-brain",
                        "provider": cloud_data.get("provider") or "GBT Cloud Brain",
                        "deep_reasoning": False,
                        "brain_mode": "cloud",
                        "metrics": llm_metrics,
                        "tokens_consumed": consumed,
                        "tokens_remaining": remaining,
                    })
                if requested_mode == "cloud":
                    return jsonify({"ok": False, "error": cloud_data.get("error") or "云端大脑调用失败"}), 502
            except Exception as cloud_err:
                if requested_mode == "cloud":
                    return jsonify({"ok": False, "error": f"云端大脑调用失败: {str(cloud_err)[:150]}"}), 502
        from gbt.llm import GBTLLM
        # 深度推理模式 → deepseek-reasoner；普通对话 → deepseek-chat / 其他模型默认
        if deep and provider == "deepseek":
            ds_cfg = PROVIDERS.get("deepseek", {})
            reasoning_model = os.environ.get("DEEPSEEK_MODEL", ds_cfg.get("default_model", "deepseek-reasoner"))
            llm = GBTLLM(provider="deepseek", api_key=api_key, model=reasoning_model)
        else:
            llm = GBTLLM(provider=provider, api_key=api_key)
            # 如果用deepseek但非推理模式，用chat模型（更快更便宜）
            if provider == "deepseek":
                chat_model = PROVIDERS.get("deepseek", {}).get("chat_model", "deepseek-chat")
                llm = GBTLLM(provider="deepseek", api_key=api_key, model=chat_model)
        resp = llm._client.chat.completions.create(
            model=llm.model, messages=[{"role": "user", "content": txt}],
            temperature=0.7, max_tokens=2048 if deep else 512)
        content = (resp.choices[0].message.content or "") if resp.choices else ""
        # 推理模型输出可能在 reasoning_content 中
        rcontent = getattr(resp.choices[0].message, "reasoning_content", None) if resp.choices else None
        usage = resp.usage
        if usage:
            llm_metrics["tokens_in"] = usage.prompt_tokens or 0
            llm_metrics["tokens_out"] = usage.completion_tokens or 0
            rct = getattr(usage, "completion_tokens_details", None)
            if rct:
                rt = getattr(rct, "reasoning_tokens", 0)
                llm_metrics["reasoning_tokens"] = rt
        llm_metrics["cost_rmb"] = round((llm_metrics["tokens_in"] * 2.5 + llm_metrics["tokens_out"] * 10) / 1000000 * 7.25, 6)
        llm_metrics["model"] = llm.model
        try:
            from gbt.auth import get_balance
            consumed = max(1, int(llm_metrics["tokens_in"]) + int(llm_metrics["tokens_out"]))
            if not get_balance().consume(user_id, consumed):
                if user_id == "_default":
                    return jsonify({
                        "ok": False,
                        "error": "当前为访客模式，Token余额为0。请先登录领取新用户10000 tokens 后再开始对话。当前版本已移除付费模块。"
                    }), 402
                return jsonify({"ok": False, "error": "Token余额不足。当前版本已移除付费模块，请专注使用电脑操控与自主操盘主能力。"}), 402
            bal = get_balance().get_balance(user_id)
            remaining = max(0, int(bal.get("tokens", 0)) - int(bal.get("used", 0)))
        except Exception:
            consumed = 0
        return jsonify({
            "ok": True,
            "response": content[:6000],
            "reasoning": rcontent[:3000] if rcontent else None,
            "model": llm.model,
            "provider": llm.provider_name,
            "deep_reasoning": deep,
            "brain_mode": "local",
            "metrics": llm_metrics,
            "tokens_consumed": consumed,
            "tokens_remaining": remaining
        })
    except Exception as e:
        err = str(e)
        if "401" in err or "Unauthorized" in err or "Invalid" in err:
            return jsonify({"ok": False, "error": "API Key无效，请检查Key是否正确"})
        if "Rate" in err or "quota" in err or "Insufficient" in err:
            return jsonify({"ok": False, "error": "API额度不足，请更换可用Key"})
        if "timeout" in err.lower() or "connect" in err.lower():
            return jsonify({"ok": False, "error": "网络超时，请检查网络连接"})
        return jsonify({"ok": False, "error": f"调用失败: {err[:150]}"})


@bp.route("/api/config/llm")
def get_llm_config():
    _load_saved_llm_env()
    from gbt.providers import AutoKeyConfig
    disc = AutoKeyConfig.scan()
    available = []
    for pid, info in disc.items():
        available.append({"id": pid, "name": info["config"]["name"], "status": info["status"],
                          "models": info["config"].get("models", [])[:5]})
    saved = _bootstrap_device_cfg_from_env()
    current = (saved.get("provider") or "auto").strip() or "auto"
    model = (saved.get("model") or "auto").strip() or "auto"
    return jsonify({
        "current": current,
        "model": model,
        "available": available,
        "saved_on_device": bool(saved.get("provider")),
        "key_masked": saved.get("key_masked"),
        "saved_provider": saved.get("provider"),
        "saved_model": saved.get("model"),
    })

def _resolve_token_user(payload=None, default_user="_default"):
    payload = payload or {}
    auth_token = (payload.get("token", "") or request.args.get("token", "") or
                  request.headers.get("X-Auth-Token", "")).strip()
    if not auth_token:
        return default_user, None
    from gbt.auth import get_auth
    username = get_auth().verify_session(auth_token)
    if not username:
        return None, (jsonify({"ok": False, "error": "会话过期，请重新登录"}), 401)
    return username, None

# ── Token 充值 API ──
