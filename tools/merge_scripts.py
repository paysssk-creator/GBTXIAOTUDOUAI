"""tools/merge_scripts.py
T-007-A 回滚工具 · 把 6 个 _script_*.html 合并回 _scripts.html。
原因：T-005/T-006 的 split 算法在花括号嵌套时误判函数边界，导致 _script_utils 内的 updateAuthUI 函数体吞掉 fmtNum/tradeState 等顶层代码，window.fmtNum 等函数 undefined。

E2E 验证发现此 regression，必须回滚。

开发者: 自由的风
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIALS_DIR = ROOT / "desktop" / "templates" / "partials"
SCRIPTS_HTML = PARTIALS_DIR / "_scripts.html"
BAK_PATH = ROOT / "data" / "preview" / "T-005" / "_scripts.html.bak"

# 按 T-005 原始顺序：_script_utils → _script_auth → _script_market → _script_pages → _script_actions → _script_init
ORDER = [
    "_script_utils", "_script_auth", "_script_market",
    "_script_pages", "_script_actions", "_script_init",
]


def merge():
    # 从 T-005 backup 恢复 _scripts.html（最稳的字节级还原）
    assert BAK_PATH.exists(), f"backup not found: {BAK_PATH}"
    SCRIPTS_HTML.write_text(BAK_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[merge] restored _scripts.html from T-005 backup: {BAK_PATH.stat().st_size} bytes")
    # 删除 6 个 partials
    for name in ORDER:
        p = PARTIALS_DIR / f"{name}.html"
        if p.exists():
            p.unlink()
            print(f"[merge] removed {p.name}")
    return SCRIPTS_HTML


if __name__ == "__main__":
    merge()
