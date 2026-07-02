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
    (re.compile(r"\beval\s*\("), "DANGER_EVAL"),
    (re.compile(r"\bexec\s*\("), "DANGER_EXEC"),
    (re.compile(r"\bos\.system\s*\("), "DANGER_OS_SYSTEM"),
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

    def _scan_file(self, fpath: str, rel: str) -> None:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return
        for pat, tag in DANGER_PATTERNS:
            m = pat.search(content)
            if m:
                self.dangers.append({
                    "file": rel, "line": 0, "type": tag,
                    "snippet": content[m.start():m.start()+80],
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
