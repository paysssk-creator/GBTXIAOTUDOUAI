"""Hugging Face Space deployment helpers for GBT Cloud Brain."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import textwrap
import time
from pathlib import Path

HF_ENV_KEYS = ["HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HUGGING_FACE_HUB_TOKEN"]


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


def _hf_env_file() -> Path:
    return _device_store_dir() / "hf_device.env"


def _hf_cfg_file() -> Path:
    return _device_store_dir() / "hf_device.json"


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
    lines = [f"{k}={v}" for k, v in env_map.items() if str(v).strip()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _read_cfg() -> dict:
    path = _hf_cfg_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_cfg(cfg: dict):
    path = _hf_cfg_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def mask_token(raw: str) -> str:
    raw = str(raw or "").strip()
    if len(raw) <= 10:
        return "*" * len(raw) if raw else ""
    return raw[:6] + "*" * max(4, len(raw) - 10) + raw[-4:]


def load_hf_token() -> str:
    env_map = _read_env_file(_hf_env_file())
    for key in HF_ENV_KEYS:
        value = os.environ.get(key, "").strip() or env_map.get(key, "").strip()
        if value:
            for alias in HF_ENV_KEYS:
                os.environ[alias] = value
            return value
    return ""


def save_hf_token(token: str) -> dict:
    token = str(token or "").strip()
    if not token:
        raise ValueError("HF token 不能为空")
    env_map = _read_env_file(_hf_env_file())
    for key in HF_ENV_KEYS:
        env_map[key] = token
        os.environ[key] = token
    _write_env_file(_hf_env_file(), env_map)
    cfg = {"saved_on_device": True, "token_masked": mask_token(token), "saved_at": int(time.time())}
    _write_cfg(cfg)
    return cfg


def get_saved_hf_config() -> dict:
    token = load_hf_token()
    cfg = _read_cfg()
    return {
        "saved_on_device": bool(token),
        "token_masked": cfg.get("token_masked") or mask_token(token),
        "saved_at": cfg.get("saved_at"),
        "env_file": str(_hf_env_file()),
    }


def load_local_llm_env() -> dict:
    try:
        from gbt.api.llm import _load_saved_llm_env
        return _load_saved_llm_env() or {}
    except Exception:
        return dict(os.environ)


def discover_cloud_secrets() -> dict:
    load_local_llm_env()
    secrets = {}
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_CHAT_MODEL", "OPENAI_API_KEY", "OPENAI_MODEL"):
        value = os.environ.get(key, "").strip()
        if value:
            secrets[key] = value
    return secrets


def _space_readme(space_title: str, repo_url: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        title: {space_title}
        emoji: 🧠
        colorFrom: blue
        colorTo: indigo
        sdk: docker
        app_port: 7860
        pinned: false
        license: mit
        ---

        # {space_title}

        GBT 的云端大脑空间，只负责推理、计划和问答，不直接执行本地高风险桌面动作。

        - 本地执行脑: 继续负责桌面控制、OCR、锚点识别、委托与持仓回读
        - 云端策略脑: 负责分析、计划、复盘、解释和结构化建议
        - 高风险动作: 必须仍由本地门禁确认

        Source: {repo_url}
        """
    )


def _space_requirements() -> str:
    return textwrap.dedent(
        """\
        Flask==3.1.3
        openai>=1.0.0,<3.0.0
        requests==2.34.2
        python-dotenv>=1.0.0,<2.0.0
        """
    )


def _space_dockerfile() -> str:
    return textwrap.dedent(
        """\
        FROM python:3.12.7-slim-bookworm

        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY app.py .

        ENV PYTHONUNBUFFERED=1 \
            PORT=7860 \
            GBT_CLOUD_ROLE=cloud-brain

        EXPOSE 7860

        CMD ["python", "app.py"]
        """
    )


def _space_app() -> str:
    return textwrap.dedent(
        """\
        import os
        from flask import Flask, jsonify, request
        from openai import OpenAI

        app = Flask(__name__)

        def _provider_config():
            if os.environ.get("DEEPSEEK_API_KEY", "").strip():
                return {
                    "provider": "DeepSeek",
                    "base_url": "https://api.deepseek.com/v1/",
                    "api_key": os.environ["DEEPSEEK_API_KEY"].strip(),
                    "model": os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-reasoner",
                }
            if os.environ.get("OPENAI_API_KEY", "").strip():
                return {
                    "provider": "OpenAI",
                    "base_url": "https://api.openai.com/v1/",
                    "api_key": os.environ["OPENAI_API_KEY"].strip(),
                    "model": os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4o-mini",
                }
            return None

        @app.get("/")
        def home():
            return '''
            <html><body style="font-family:Arial;padding:24px;background:#0b1020;color:#fff">
            <h1>GBT Cloud Brain</h1>
            <p>云端只负责推理与计划，不直接接管本地电脑。</p>
            <p>接口: GET /api/status, POST /api/chat, POST /api/plan</p>
            </body></html>
            '''

        @app.get("/api/status")
        def status():
            cfg = _provider_config()
            return jsonify({
                "ok": True,
                "role": "cloud-brain",
                "provider": (cfg or {}).get("provider"),
                "model": (cfg or {}).get("model"),
                "release_tag": os.environ.get("GBT_RELEASE_TAG", "hf-space"),
            })

        def _call_llm(system_prompt: str, user_prompt: str):
            cfg = _provider_config()
            if not cfg:
                return False, "未配置云端模型密钥", None
            client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=60)
            resp = client.chat.completions.create(
                model=cfg["model"],
                temperature=0.2,
                max_tokens=1200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (resp.choices[0].message.content or "") if resp.choices else ""
            return True, content[:6000], cfg

        @app.post("/api/chat")
        def chat():
            payload = request.get_json(silent=True) or {}
            text = str(payload.get("text", "")).strip()
            if not text:
                return jsonify({"ok": False, "error": "text 不能为空"}), 400
            ok, content, cfg = _call_llm(
                "你是 GBT 的云端策略脑，只做分析、计划、解释，不直接下达本地危险动作。",
                text,
            )
            if not ok:
                return jsonify({"ok": False, "error": content}), 400
            return jsonify({"ok": True, "response": content, "provider": cfg["provider"], "model": cfg["model"]})

        @app.post("/api/plan")
        def plan():
            payload = request.get_json(silent=True) or {}
            objective = str(payload.get("objective", "")).strip()
            context = str(payload.get("context", "")).strip()
            if not objective:
                return jsonify({"ok": False, "error": "objective 不能为空"}), 400
            prompt = "请输出结构化操盘计划，字段包含: summary, checks, action_plan, risk_points, rollback_trigger。\\n目标: " + objective + "\\n上下文: " + context
            ok, content, cfg = _call_llm(
                "你是 GBT 的云端策略脑，请输出严谨、可执行、可回滚的结构化交易计划。",
                prompt,
            )
            if not ok:
                return jsonify({"ok": False, "error": content}), 400
            return jsonify({"ok": True, "plan": content, "provider": cfg["provider"], "model": cfg["model"]})

        if __name__ == "__main__":
            port = int(os.environ.get("PORT", "7860"))
            app.run(host="0.0.0.0", port=port, debug=False)
        """
    )


def build_space_bundle(target_dir: str | Path, space_title: str, repo_url: str):
    target = Path(target_dir)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    (target / "README.md").write_text(_space_readme(space_title, repo_url), encoding="utf-8")
    (target / "requirements.txt").write_text(_space_requirements(), encoding="utf-8")
    (target / "Dockerfile").write_text(_space_dockerfile(), encoding="utf-8")
    (target / "app.py").write_text(_space_app(), encoding="utf-8")
    return target


def stage_space_bundle(space_title: str, repo_url: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="gbt_hf_space_"))
    return build_space_bundle(root, space_title=space_title, repo_url=repo_url)
