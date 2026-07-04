"""gbt/templates/composer.py
T-004 · 把 layout.html 拆成的 17 个 partials 字节级拼回完整 HTML。
供 desktop_app.py / desktop/app.py / blueprint 共用。

开发者: 自由的风
"""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = ROOT / "desktop" / "templates"
PARTIALS_DIR = TEMPLATES_DIR / "partials"
SHELL_PATH = TEMPLATES_DIR / "layout.shell.html"

PARTIAL_NAMES = [
    "_head", "_side", "_topbar",
    "_tab_dash", "_tab_pilot", "_tab_llm", "_tab_chat", "_tab_trade",
    "_tab_account", "_tab_auth", "_tab_desktop",
    "_tab_mcp", "_tab_connect",
    "_toast", "_scripts",
]


def _read_shell() -> str:
    if not SHELL_PATH.exists():
        return ""
    return SHELL_PATH.read_text(encoding="utf-8")


def _read_partial(name: str) -> str:
    p = PARTIALS_DIR / f"{name}.html"
    if not p.exists():
        return f"<!-- MISSING PARTIAL: {name} -->"
    return p.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def compose_dash_html() -> str:
    """读取 dashboard HTML。
    `layout.html` 作为当前唯一正式来源，避免 partials 与正式运行模板漂移。
    """
    legacy = TEMPLATES_DIR / "layout.html"
    if legacy.exists():
        return legacy.read_text(encoding="utf-8")
    if not PARTIALS_DIR.exists():
        return "<h1>GBT Pro</h1>"

    out_parts = []
    for name in PARTIAL_NAMES:
        out_parts.append(_read_partial(name))
    return "".join(out_parts)


def partials_summary() -> dict:
    """partials 健康摘要（供 healthcheck 探针用）"""
    if not PARTIALS_DIR.exists():
        return {"ok": False, "reason": "partials dir missing"}
    items = []
    total = 0
    for name in PARTIAL_NAMES:
        p = PARTIALS_DIR / f"{name}.html"
        if p.exists():
            size = p.stat().st_size
            total += size
            items.append({"name": f"{name}.html", "bytes": size, "exists": True})
        else:
            items.append({"name": f"{name}.html", "bytes": 0, "exists": False})
    return {
        "ok": all(x["exists"] for x in items),
        "partials_count": len(items),
        "total_bytes": total,
        "items": items,
    }
