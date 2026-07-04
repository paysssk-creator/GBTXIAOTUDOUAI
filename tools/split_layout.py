"""tools/split_layout.py
T-004 · 把 desktop/templates/layout.html 切成 17 个 partials。
本脚本可重复运行：每次执行都会重新扫描 layout.html 锚点 + 切割 + 拼回。
roundtrip 校验："partials 拼接结果 == layout.html 字节级一致"。

开发者: 自由的风
"""
from __future__ import annotations
import os, sys, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "desktop" / "templates" / "layout.html"
PARTIALS_DIR = ROOT / "desktop" / "templates" / "partials"
BAK_PATH = ROOT / "data" / "preview" / "T-004" / "layout.html.bak"

# ── 17 个 partial 的 [name, anchor_pattern] ──
# 用 anchor_pattern 在 layout.html 中找起始行；end 行 = 下一个 partial 的 start - 1
# 不写死行号，layout.html 改了 anchor 仍可自适应
ANCHORS = [
    ("_head.html",        r"^<!DOCTYPE html>"),
    ("_side.html",        r'<aside id="side">'),
    ("_topbar.html",      r'<div id="topbar">'),
    ("_tab_dash.html",    r'<div class="tab-panel active" id="panel-dash">'),
    ("_tab_pilot.html",   r'<div class="tab-panel" id="panel-pilot">'),
    ("_tab_llm.html",     r'<div class="tab-panel" id="panel-llm">'),
    ("_tab_chat.html",    r'<div class="tab-panel" id="panel-chat">'),
    ("_tab_trade.html",   r'<div class="tab-panel" id="panel-trade">'),
    ("_tab_account.html", r'<div class="tab-panel" id="panel-account">'),
    ("_tab_auth.html",    r'<div class="tab-panel" id="panel-auth">'),
    ("_tab_hacker.html",  r'<div class="tab-panel" id="panel-hacker">'),
    ("_tab_desktop.html", r'<div class="tab-panel" id="panel-desktop">'),
    ("_tab_mcp.html",     r'<div class="tab-panel" id="panel-mcp">'),
    ("_tab_connect.html", r'<div class="tab-panel" id="panel-connect">'),
    ("_tab_recharge.html",r'<div class="tab-panel" id="panel-recharge">'),
    ("_toast.html",       r'<div id="toast"></div>'),
    ("_scripts.html",     r'<script>'),
]


def _scan_anchors(text: str) -> list[tuple[str, int, int]]:
    """扫描 layout.html，返回 [(name, start_line, end_line), ...] 1-based 闭区间"""
    lines = text.splitlines(keepends=True)
    n = len(lines)
    starts = []
    for name, pat in ANCHORS:
        rgx = re.compile(pat)
        for i, line in enumerate(lines, 1):
            if rgx.search(line):
                starts.append((name, i))
                break
        else:
            raise RuntimeError(f"anchor for {name!r} ({pat!r}) not found in layout.html")
    # 计算 end
    plan = []
    for idx, (name, s) in enumerate(starts):
        if idx + 1 < len(starts):
            e = starts[idx + 1][1] - 1
        else:
            e = n
        plan.append((name, s, e))
    return plan


def split():
    assert LAYOUT.exists(), f"layout.html not found: {LAYOUT}"
    text = LAYOUT.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    n = len(lines)
    print(f"[split] layout.html: {n} lines, {len(text)} bytes")

    PARTIALS_DIR.mkdir(parents=True, exist_ok=True)

    plan = _scan_anchors(text)
    written = []
    for name, s, e in plan:
        chunk = "".join(lines[s - 1:e])  # inclusive
        out = PARTIALS_DIR / name
        out.write_text(chunk, encoding="utf-8")
        written.append((name, s, e, len(chunk)))
        print(f"  + {name:24s} L{s:4d}..{e:4d} ({len(chunk):6d} bytes)")

    # 重写 layout.html = partials 拼装（保证字节级一致）
    composed = "".join((PARTIALS_DIR / name).read_text(encoding="utf-8") for name, _, _ in plan)
    LAYOUT.write_text(composed, encoding="utf-8")
    print(f"[split] layout.html rewritten: {len(composed)} bytes")

    # 备份
    BAK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BAK_PATH.write_text(text, encoding="utf-8")
    print(f"[split] backup: {BAK_PATH} ({len(text)} bytes)")

    return written


def check_roundtrip():
    """校验 partials 拼装结果 == layout.html 字节级一致"""
    from gbt.templates.composer import compose_dash_html
    composed_by_composer = compose_dash_html()
    layout_bytes = LAYOUT.read_text(encoding="utf-8")
    if composed_by_composer == layout_bytes:
        return {
            "roundtrip_ok": True,
            "composer_bytes": len(composed_by_composer),
            "layout_bytes": len(layout_bytes),
            "diff_bytes": 0,
        }
    # 写 diff 报告
    diff_path = ROOT / "data" / "preview" / "T-004" / "roundtrip-diff.txt"
    with open(diff_path, "w", encoding="utf-8") as f:
        for i, (a, b) in enumerate(zip(layout_bytes, composed_by_composer)):
            if a != b:
                ctx_start = max(0, i - 40)
                f.write(f"[DIFF @ byte {i}]\n")
                f.write(f"  layout[{ctx_start}:{ctx_start+80}] = {layout_bytes[ctx_start:ctx_start+80]!r}\n")
                f.write(f"  composer[{ctx_start}:{ctx_start+80}] = {composed_by_composer[ctx_start:ctx_start+80]!r}\n")
                break
        f.write(f"\nlen(layout)={len(layout_bytes)}  len(composer)={len(composed_by_composer)}\n")
    return {
        "roundtrip_ok": False,
        "composer_bytes": len(composed_by_composer),
        "layout_bytes": len(layout_bytes),
        "diff_bytes": abs(len(layout_bytes) - len(composed_by_composer)),
        "diff_report": str(diff_path),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true", help="执行切割 + 拼回")
    ap.add_argument("--check-roundtrip", action="store_true", help="仅校验拼装 vs layout.html 字节级一致")
    args = ap.parse_args()
    if args.check_roundtrip:
        r = check_roundtrip()
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["roundtrip_ok"] else 1)
    if args.split:
        written = split()
        print(f"\n[split] {len(written)} partials written under {PARTIALS_DIR}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
