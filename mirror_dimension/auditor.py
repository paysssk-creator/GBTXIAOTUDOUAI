# -*- coding: utf-8 -*-
"""深度审计引擎 — 敏感文件 + .gitignore + 未跟踪风险"""
import os, subprocess
from typing import List

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".gbt", "data", ".idea", ".vscode",
    "AppData", "Library", ".github", "output", "vendor",
    "venv_cradle", "venv_cradle_py310", "site-packages", "Lib",
    "backup", "archive", "old", "sandbox-logs", "monitoring.db",
    "logs", "screenshots", "installer",
}

SENSITIVE_FILE_PATTERNS = [
    ".env", ".pem", ".key", "credentials", "secret",
    ".db", ".sqlite", "password",
]

REQUIRED_GITIGNORE_RULES = [
    ".env", "*.db", "*.sqlite", "*.pem", "*.key",
    "__pycache__", "*.pyc", "data/",
]


class ProjectAuditor:
    """深度安全审计器"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)

    def audit(self) -> dict:
        results = {
            "project": self.root,
            "sensitive_files": self._check_sensitive(),
            "gitignore_gaps": self._check_gitignore(),
            "untracked_risks": self._check_untracked(),
            "config_status": self._check_config(),
        }
        all_ok = (
            not results["sensitive_files"]
            and not results["gitignore_gaps"]
            and not results["untracked_risks"]
        )
        results["clean"] = all_ok
        return results

    def _check_sensitive(self) -> List[str]:
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                for pat in SENSITIVE_FILE_PATTERNS:
                    if pat in fname.lower():
                        found.append(os.path.relpath(
                            os.path.join(dirpath, fname), self.root))
                        break
        return found

    def _check_gitignore(self) -> List[str]:
        gi = os.path.join(self.root, ".gitignore")
        if not os.path.exists(gi):
            return ["NO_GITIGNORE_FILE"]
        with open(gi, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [r for r in REQUIRED_GITIGNORE_RULES if r not in content]

    def _check_untracked(self) -> List[str]:
        try:
            r = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.root, capture_output=True, text=True, timeout=15,
            )
            untracked = r.stdout.strip().split("\n") if r.stdout.strip() else []
        except Exception:
            return []
        return [
            f for f in untracked
            if any(p in f.lower() for p in SENSITIVE_FILE_PATTERNS)
        ]

    def _check_config(self) -> dict:
        cfgs = {}
        for name in [".env.example", "pyproject.toml", "requirements.txt"]:
            cfgs[name] = os.path.exists(os.path.join(self.root, name))
        return cfgs


def audit_project(root: str) -> dict:
    """便捷审计函数"""
    return ProjectAuditor(root).audit()
