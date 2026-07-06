"""stdio MCP 外部 AI 桥接器。

通过本地 GBT Runtime 的 HTTP 接口复用已配置的外部大模型能力，
给 UniversalMCP 提供一个稳定的 subprocess/stdin 风格接入口。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8765"


def _request_json(path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(body or "{}")


def _emit(payload: dict, exit_code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    return exit_code


def main(argv: list[str]) -> int:
    method = (argv[1] if len(argv) > 1 else "ping").strip().lower()
    prompt = " ".join(a for a in argv[2:] if a).strip()
    try:
        if method == "ping":
            _, providers = _request_json("/api/providers")
            available = sorted([k for k, v in providers.items() if v.get("status") == "available"])
            return _emit({
                "ok": True,
                "method": "ping",
                "base_url": BASE_URL,
                "available_providers": available,
                "provider_count": len(available),
            })
        if method == "chat":
            if not prompt:
                prompt = "请只回复：MCP 外部 AI 已联通"
            _, body = _request_json("/api/chat", {"text": prompt})
            ok = bool(body.get("ok"))
            return _emit({
                "ok": ok,
                "method": "chat",
                "provider": body.get("provider"),
                "model": body.get("model"),
                "response": body.get("response"),
                "error": body.get("error"),
            }, 0 if ok else 1)
        return _emit({"ok": False, "error": f"unsupported method: {method}"}, 2)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return _emit({"ok": False, "error": f"http {e.code}", "detail": detail[:500]}, 1)
    except Exception as e:
        return _emit({"ok": False, "error": str(e)[:300]}, 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
