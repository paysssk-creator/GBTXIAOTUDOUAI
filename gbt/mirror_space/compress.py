"""GBT Pro — mirror space · compress shim
──────────────────────────────────────────────
上游 sandbox-orchestrator.py 通过 `import compress` 调用两个函数：
  · compress.summarize_report(report_path)      -> str
  · compress.summarize_fix_history(module, rounds=3) -> str

本 shim 在镜像空间目录就地提供这两个函数，避免对 pip 上不存在的
私有 `compress` 包形成依赖。
"""

# 开发者: 自由的风

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def _truncate(text: str, limit: int = 320) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _read_report(p):
    try:
        p = Path(p)
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8", errors="ignore") or "{}")
    except Exception:
        return {}


def summarize_report(report_path) -> str:
    """把评审报告压成一行中文摘要，便于人读 / 日志快速浏览。"""
    rep = _read_report(report_path)
    if not rep:
        return "(报告为空或不可读)"
    module = rep.get("module") or Path(report_path).stem
    tests = rep.get("tests") or {}
    audit = rep.get("audit") or {}
    build = rep.get("build") or {}
    secrets = rep.get("secrets") or {}
    return (
        f"[{module}] "
        f"tests={tests.get('passed', 0)}P/{tests.get('failed', 0)}F "
        f"build={'OK' if build.get('ok') else 'FAIL'} "
        f"audit={'OK' if audit.get('ok') else 'FAIL'} "
        f"secrets={len(secrets.get('findings', []))}"
    )


def summarize_fix_history(module: str, rounds: int = 3) -> str:
    """回看最近 rounds 轮的评审轨迹，生成可读历史摘要。"""
    home = Path(__import__("os").environ.get("USERPROFILE") or __import__("os").environ.get("HOME") or ".")
    reports_dir = home / ".gbt" / "sandbox" / "reports"
    lines = [f"HISTORY (last {rounds}) for {module}:"]
    if not reports_dir.exists():
        lines.append("  (无 reports 目录)")
        return "\n".join(lines)
    files = sorted(
        [p for p in reports_dir.glob(f"{module}-*-review.json")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )[: max(1, int(rounds or 1))]
    if not files:
        lines.append("  (无历史评审)")
        return "\n".join(lines)
    for f in files:
        try:
            ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d %H:%M")
        except Exception:
            ts = "--"
        lines.append(f"  · {ts}  {_truncate(summarize_report(f))}")
    return "\n".join(lines)