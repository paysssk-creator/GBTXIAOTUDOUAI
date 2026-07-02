# -*- coding: utf-8 -*-
"""全量扫描引擎 — 危险模式 + 虚假代码 + 语法检查"""
import os, re, time
from typing import List, Dict

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".gbt", "data", ".idea", ".vscode",
    "AppData", "Library", ".github", "output", "vendor",
    "venv_cradle", "venv_cradle_py310", "site-packages", "Lib",
    "backup", "archive", "old", "sandbox-logs", "monitoring.db",
    "logs", "screenshots", "installer",
    # 独立子项目 / 非 Python 核心源码
    "app", "src-tauri", ".claude", ".codewhale", ".pytest_cache",
}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json",
             ".yaml", ".yml", ".toml", ".sh", ".bat", ".ps1",
             ".html", ".css", ".md", ".env", ".txt"}

DANGER_PATTERNS = [
    (re.compile(r"API_KEY\s*=\s*['\"][^'\"]{20,}['\"]", re.I), "HARDCODE_API_KEY"),
    (re.compile(r"password\s*=\s*['\"][^'\"]{6,}['\"]", re.I), "HARDCODE_PASSWORD"),
    (re.compile(r"token\s*=\s*['\"][^'\"]{20,}['\"]", re.I), "HARDCODE_TOKEN"),
    (re.compile(r"secret\s*=\s*['\"][^'\"]{8,}['\"]", re.I), "HARDCODE_SECRET"),
    (re.compile(r"['\"]sk-[a-zA-Z0-9]{20,}['\"]"), "OPENAI_KEY_LEAK"),
    # 负向回顾防止字符串内的子串匹配 (如 \"eval(\" / 'exec(' 等)
    (re.compile(r"(?<!['\"])\beval\s*\("), "DANGER_EVAL"),
    (re.compile(r"(?<!['\"])\bexec\s*\("), "DANGER_EXEC"),
    (re.compile(r"(?<!['\"])\bos\.system\s*\("), "DANGER_OS_SYSTEM"),
    (re.compile(r"subprocess\.(?:call|run|Popen)\s*\(.+shell\s*=\s*True"), "DANGER_SHELL_TRUE"),
    (re.compile(r"^(\s*)except\s*:", re.MULTILINE), "BARE_EXCEPT"),
]

FAKE_PATTERNS = [
    (re.compile(r"#\s*TODO.*", re.I), "TODO_PLACEHOLDER"),
    (re.compile(r"#\s*FIXME.*", re.I), "FIXME_PLACEHOLDER"),
    (re.compile(r"#\s*HACK.*", re.I), "HACK_MARKER"),
    (re.compile(r"raise\s+NotImplementedError"), "NOT_IMPLEMENTED"),
    (re.compile(r"return\s+None\s*#.*TODO"), "STUB_RETURN_NONE"),
    (re.compile(r"=\s*['\"]test['\"]", re.I), "FAKE_TEST_DATA"),
    (re.compile(r"=\s*['\"]placeholder['\"]", re.I), "FAKE_PLACEHOLDER"),
    (re.compile(r"=\s*['\"]mock['\"]", re.I), "FAKE_MOCK"),
    (re.compile(r"=\s*['\"]dummy['\"]", re.I), "FAKE_DUMMY"),
    (re.compile(r"=\s*['\"]fake['\"]", re.I), "FAKE_FAKE"),
]


# 合理用途白名单: (文件路径片段, 危险类型) — 这些模式在特定上下文中是正当的
SAFE_DANGER_WHITELIST = {
    ("_test_step.py", "DANGER_EXEC"): "测试工具动态导入验证",
    ("gbt/agents.py", "DANGER_OS_SYSTEM"): "系统音量控制面板调用",
    ("gbt/desktop_app.py", "BARE_EXCEPT"): "GUI 组件的安全容错回退",
    ("gbt\\agents.py", "DANGER_OS_SYSTEM"): "系统音量控制面板调用",
    ("gbt\\desktop_app.py", "BARE_EXCEPT"): "GUI 组件的安全容错回退",
}


class ProjectScanner:
    """全量项目扫描器"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)
        self.dangers: List[dict] = []
        self.fakes: List[dict] = []
        self.syntax_errors: List[dict] = []
        self.total_files = 0

    def scan(self) -> dict:
        t0 = time.time()
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in CODE_EXTS:
                    continue
                fpath = os.path.join(dirpath, fname)
                rel = os.path.relpath(fpath, self.root)
                self.total_files += 1
                self._scan_file(fpath, rel)
                if ext == ".py":
                    self._check_syntax(fpath, rel)

        clean = not (self.dangers or self.syntax_errors)
        return {
            "project": self.root,
            "total_files": self.total_files,
            "dangers": len(self.dangers),
            "fakes": len(self.fakes),
            "syntax_errors": len(self.syntax_errors),
            "danger_items": self.dangers,
            "fake_items": self.fakes,
            "syntax_items": self.syntax_errors,
            "duration_s": round(time.time() - t0, 2),
            "clean": clean,
        }

    def _strip_comments_and_strings(self, content: str, ext: str) -> str:
        """移除注释和字符串字面量（tokenize 定位 + 字符级替换）。仅对 .py 处理。"""
        if ext != ".py":
            return content
        try:
            import tokenize, io
            # 构建行首字符索引表: line_starts[行号0-based] = 该行首字符在文件中的绝对位置
            line_starts = [0]
            for i, ch in enumerate(content):
                if ch == "\n":
                    line_starts.append(i + 1)
            # 收集屏蔽区间
            spans = []
            tokens = tokenize.generate_tokens(io.StringIO(content).readline)
            for tok in tokens:
                if tok.type in (tokenize.STRING, tokenize.COMMENT):
                    # tok.start = (行号1-based, 列偏移0-based)
                    # tok.end   = (行号1-based, 列偏移0-based)
                    sl, sc = tok.start  # 起始行, 起始列
                    el, ec = tok.end    # 结束行, 结束列
                    abs_start = line_starts[sl - 1] + sc if sl - 1 < len(line_starts) else sc
                    abs_end   = line_starts[el - 1] + ec if el - 1 < len(line_starts) else ec
                    spans.append((abs_start, abs_end))
            if not spans:
                return content
            # 合并重叠区间
            spans.sort()
            merged = []
            for s, e in spans:
                if merged and s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                else:
                    merged.append((s, e))
            # 字符替换
            chars = list(content)
            for s, e in merged:
                for i in range(s, min(e, len(chars))):
                    if chars[i] not in ("\n", "\r"):
                        chars[i] = " "
            return "".join(chars)
        except Exception:
            pass
        return content

    def _scan_file(self, fpath: str, rel: str) -> None:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return
        ext = os.path.splitext(fpath)[1].lower()
        # 对 .md 文件只做假数据扫描，跳过危险模式
        if ext == ".md":
            for i, line in enumerate(content.split("\n"), 1):
                for pat, tag in FAKE_PATTERNS:
                    if pat.search(line):
                        self.fakes.append({
                            "file": rel, "line": i, "type": tag,
                            "snippet": line.strip()[:100],
                        })
            return
        # 对代码文件：用清理后的内容做危险扫描，原始内容做假数据扫描
        clean = self._strip_comments_and_strings(content, ext)
        for pat, tag in DANGER_PATTERNS:
            m = pat.search(clean)
            if m:
                # 检查白名单：合理用途跳过
                if (rel, tag) in SAFE_DANGER_WHITELIST:
                    continue
                raw_snippet = content[m.start():m.start()+80] if m.start() < len(content) else ""
                self.dangers.append({
                    "file": rel, "line": 0, "type": tag,
                    "snippet": raw_snippet,
                })
        for i, line in enumerate(content.split("\n"), 1):
            for pat, tag in FAKE_PATTERNS:
                if pat.search(line):
                    self.fakes.append({
                        "file": rel, "line": i, "type": tag,
                        "snippet": line.strip()[:100],
                    })

    def _check_syntax(self, fpath: str, rel: str) -> None:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                compile(f.read(), fpath, "exec")
        except SyntaxError as e:
            self.syntax_errors.append({
                "file": rel, "line": e.lineno or 0,
                "type": "SYNTAX_ERROR", "snippet": str(e),
            })
        except Exception:
            pass


def scan_project(root: str) -> dict:
    """便捷扫描函数"""
    return ProjectScanner(root).scan()
