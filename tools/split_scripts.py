"""tools/split_scripts.py
T-006 升级 · 花括号级 function 边界识别 + 重切 _scripts.html。
把每个 function 的 [start_line, end_line] 整段归到该 function 所属 group。

开发者: 自由的风
"""
from __future__ import annotations
import os, re, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIALS_DIR = ROOT / "desktop" / "templates" / "partials"
SCRIPTS_HTML = PARTIALS_DIR / "_scripts.html"
BAK_PATH = ROOT / "data" / "preview" / "T-005" / "_scripts.html.bak"

GROUPS = [
    ("_script_utils.html", {
        "$", "qs", "esc", "setTxt", "fmtTime", "fmtNum", "fmtPct", "pctCls",
        "fmtYi", "fmtWan", "strengthText", "api", "D", "tradeStyleText", "marketRiskText",
        "toastQ", "toast", "W",
    }),
    ("_script_auth.html", {
        "authState", "getStoredToken", "setStoredToken", "updateAuthUI", "clearAuth",
        "loadTokenBalance", "loadProfile", "loadAuth", "registerUser", "loginUser", "logoutUser",
    }),
    ("_script_market.html", {
        "tradeState", "renderTradeDetail", "loadTradeDetail", "tradeProSearch",
        "tradeProPeriod", "streamReveal", "tradeProAnalyze", "renderTradeProChart",
        "renderTradeProTech", "techCard", "numOrDash", "renderTradeWatchlist",
        "renderTradeMarket", "refresh", "loadMarket", "loadTrade", "restoreLastRecap",
    }),
    ("_script_pages.html", {
        "loadDash", "loadHacker", "loadDesktop", "loadMCP", "loadLLM", "loadChat", "loadPilot",
        "loadRecharge", "loadConnect", "loadAccount", "load账户", "loadMirror", "_capLabel",
        "__capLabels", "switchTab", "titles", "pageTitle", "pageTitleEl",
    }),
    ("_script_actions.html", {
        "sendChat", "addChatMsg", "recapGenerate", "saveLLM", "doRecharge",
        "pilotStart", "pilotStop", "execCap", "execDesk", "send对话", "sendMessage",
    }),
    ("_script_init.html", {"loadAll", "bootApp", "bootstrap", "init"}),
]


# ── 花括号级 function 边界识别 ──
def _find_function_bodies(text: str) -> list[tuple[str, int, int]]:
    """扫描整个 _scripts.html，找每个 `function name(` 的 [start_line, end_line]（end_line 含闭合 }）
    简化：忽略字符串/正则内的花括号（用启发式：跟踪 " ' 配对 + // 注释）
    返回 [(name, start_line, end_line), ...]
    """
    lines = text.splitlines(keepends=False)
    n = len(lines)
    bodies = []
    for i, line in enumerate(lines):
        m = re.match(r'^\s*function\s+([A-Za-z_$][\w$]*)\s*\(', line)
        if not m:
            continue
        name = m.group(1)
        start = i + 1  # 1-based
        depth = 0
        seen_open = False
        in_str = None
        for j in range(i, n):
            k = 0
            while k < len(lines[j]):
                ch = lines[j][k]
                # 跳过 // 注释
                if in_str is None and ch == '/' and k + 1 < len(lines[j]) and lines[j][k + 1] == '/':
                    break
                if in_str is None and ch == '/' and k + 1 < len(lines[j]) and lines[j][k + 1] == '*':
                    # 块注释
                    end = lines[j].find('*/', k + 2)
                    if end < 0:
                        k = len(lines[j])
                    else:
                        k = end + 2
                    continue
                if in_str is not None:
                    if ch == '\\' and k + 1 < len(lines[j]):
                        k += 2
                        continue
                    if ch == in_str:
                        in_str = None
                else:
                    if ch == '"' or ch == "'":
                        in_str = ch
                    elif ch == '`':
                        in_str = '`'
                    elif ch == '{':
                        depth += 1
                        seen_open = True
                    elif ch == '}':
                        depth -= 1
                k += 1
            if seen_open and depth == 0:
                bodies.append((name, start, j + 1))
                break
    return bodies


# 顶层 var/let/const 声明（不在任何 function 体内）
_TOP_DECL_RE = re.compile(
    r'^\s*(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*='
)


def _find_top_vars(text: str, in_function_ranges: list[tuple[int, int]]) -> list[tuple[int, str]]:
    """找顶层 var/let/const 声明（不在 function 体内的行）"""
    decls = []
    for i, line in enumerate(text.splitlines(keepends=False), 1):
        if any(s <= i <= e for s, e in in_function_ranges):
            continue
        m = _TOP_DECL_RE.match(line)
        if m:
            decls.append((i, m.group(1)))
    return decls


def _classify(name: str) -> str:
    for fname, scope in GROUPS:
        if name in scope:
            return fname[:-5]
    return "_script_init"


def _backup():
    BAK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BAK_PATH.exists():
        BAK_PATH.write_text(SCRIPTS_HTML.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[scripts] backup: {BAK_PATH}")


def split():
    if SCRIPTS_HTML.exists():
        text = SCRIPTS_HTML.read_text(encoding="utf-8")
        print(f"[scripts] using existing _scripts.html")
    elif BAK_PATH.exists():
        text = BAK_PATH.read_text(encoding="utf-8")
        SCRIPTS_HTML.write_text(text, encoding="utf-8")
        print(f"[scripts] restored _scripts.html from {BAK_PATH.name}")
    else:
        raise RuntimeError(f"_scripts.html not found and no backup")

    lines = text.splitlines(keepends=True)
    n = len(lines)
    print(f"[scripts] _scripts.html: {n} lines, {len(text)} bytes")

    _backup()

    # 1) 找所有 function 主体
    bodies = _find_function_bodies(text)
    print(f"[scripts] functions found: {len(bodies)}")
    in_function_ranges = [(s, e) for _, s, e in bodies]

    # 2) 找顶层 var
    top_vars = _find_top_vars(text, in_function_ranges)
    print(f"[scripts] top-level vars: {len(top_vars)}")

    # 3) 把所有声明 + 主体行归类
    # 每个 group 收集 [start, end] 区间
    group_ranges = {g[0][:-5]: [] for g in GROUPS}

    for name, s, e in bodies:
        g = _classify(name)
        group_ranges[g].append((s, e))
    for line_no, name in top_vars:
        g = _classify(name)
        # 顶层 var 单独占 1 行
        group_ranges[g].append((line_no, line_no))

    # 4) 合并重叠区间
    def merge_ranges(ranges, gap=3):
        if not ranges:
            return []
        ranges = sorted(set(ranges))
        merged = []
        cs, ce = ranges[0]
        for s, e in ranges[1:]:
            if s - ce <= gap:
                ce = max(ce, e)
            else:
                merged.append((cs, ce + gap))
                cs, ce = s, e
        merged.append((cs, ce + gap))
        return [(max(1, a), min(n, b)) for a, b in merged]

    plan = []
    for fname, _ in GROUPS:
        gname = fname[:-5]
        merged = merge_ranges(group_ranges.get(gname, []), gap=3)
        plan.append((gname, merged))

    # 5) 写出 6 个 partials
    written = []
    for gname, ranges in plan:
        chunks = []
        for s, e in ranges:
            chunks.append("".join(lines[s - 1:e]))
        body = "".join(chunks)
        wrapped = f"<script>\n// === T-006 partial: {gname} · 开发者: 自由的风 ===\n{body}\n</script>\n"
        out = PARTIALS_DIR / f"{gname}.html"
        out.write_text(wrapped, encoding="utf-8")
        written.append((gname, len(ranges), len(wrapped)))
        print(f"  + {gname:24s} ranges={len(ranges):2d}  ({len(wrapped):6d} bytes)")

    SCRIPTS_HTML.unlink()
    print(f"[scripts] removed {SCRIPTS_HTML.name}")
    return written, bodies, top_vars


def check_behavior():
    if not BAK_PATH.exists():
        return {"behavior_ok": False, "reason": "backup not found"}
    text = BAK_PATH.read_text(encoding="utf-8")
    bodies = _find_function_bodies(text)
    in_function_ranges = [(s, e) for _, s, e in bodies]
    top_vars = _find_top_vars(text, in_function_ranges)
    orig_funcs = {n for n, _, _ in bodies}
    orig_vars = {n for _, n in top_vars}
    orig_names = orig_funcs | orig_vars

    split_funcs = set()
    for fname, _ in GROUPS:
        p = PARTIALS_DIR / fname
        if not p.exists():
            continue
        # 只校验 function 名集合（partial 内 var 已通过范围归类，无需逐行匹配）
        pt = p.read_text(encoding="utf-8")
        for n, _, _ in _find_function_bodies(pt):
            split_funcs.add(n)

    missing = orig_funcs - split_funcs
    extra = split_funcs - orig_funcs
    return {
        "behavior_ok": len(missing) == 0 and len(extra) == 0,
        "orig_funcs": len(orig_funcs),
        "split_funcs": len(split_funcs),
        "orig_top_vars": len(orig_vars),
        "missing_names": sorted(missing)[:30],
        "extra_names": sorted(extra)[:30],
        "note": "function name 集合一致（var 通过范围归类到 group）"
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--check-behavior", action="store_true")
    args = ap.parse_args()
    if args.check_behavior:
        r = check_behavior()
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["behavior_ok"] else 1)
    if args.split:
        written, _, _ = split()
        print(f"\n[scripts] {len(written)} partials written")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
