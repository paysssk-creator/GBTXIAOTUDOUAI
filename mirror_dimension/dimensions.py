# -*- coding: utf-8 -*-
"""四维度测试引擎 — 用户/开发者/运维/安全"""
import os
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".gbt", "data", ".idea", ".vscode",
    "Library", ".github", "output", "vendor",
    "venv_cradle", "venv_cradle_py310", "site-packages", "Lib",
}

def _should_skip(path_str: str) -> bool:
    """检查路径的任意部分是否匹配跳过目录"""
    parts = set(path_str.replace("\\", "/").split("/"))
    return bool(parts & SKIP_DIRS)


class DimensionTester:
    """四维度测试器"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)

    def test(self) -> dict:
        dims = {}
        dims["user"] = self._dim_user()
        dims["developer"] = self._dim_developer()
        dims["ops"] = self._dim_ops()
        dims["security"] = self._dim_security()
        scores = [d.get("score", 0) for d in dims.values()]
        avg = sum(scores) / max(len(scores), 1)
        return {
            "project": self.root,
            "user": dims["user"],
            "developer": dims["developer"],
            "ops": dims["ops"],
            "security": dims["security"],
            "average_score": round(avg, 1),
            "verdict": "PASS" if avg >= 60 else "WARN" if avg >= 40 else "FAIL",
        }

    def _dim_user(self) -> dict:
        entries = ["main.py", "entry.py", "agent_entry.py", "app/__init__.py"]
        has_entry = any(os.path.exists(os.path.join(self.root, e)) for e in entries)
        has_readme = os.path.exists(os.path.join(self.root, "README.md"))
        return {
            "has_entry": has_entry, "has_readme": has_readme,
            "score": (10 if has_entry else 0) + (10 if has_readme else 0),
        }

    def _dim_developer(self) -> dict:
        py_files = [f for f in Path(self.root).rglob("*.py") if not _should_skip(str(f))]
        with_doc = 0
        for fp in py_files[:200]:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    if '"""' in f.readline():
                        with_doc += 1
            except Exception:
                pass
        doc_rate = round(with_doc / max(len(py_files[:200]), 1) * 100, 1)
        return {
            "python_file_count": len(py_files),
            "docstring_rate": doc_rate,
            "score": min(round(doc_rate / 5), 20),
        }

    def _dim_ops(self) -> dict:
        has_docker = os.path.exists(os.path.join(self.root, "Dockerfile"))
        has_compose = os.path.exists(os.path.join(self.root, "docker-compose.yml"))
        has_logging = False
        for fp in list(Path(self.root).rglob("*.py"))[:100]:
            if _should_skip(str(fp)):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    if "import logging" in f.read(8192):
                        has_logging = True
                        break
            except Exception:
                pass
        return {
            "has_dockerfile": has_docker,
            "has_docker_compose": has_compose,
            "uses_logging": has_logging,
            "score": (10 if (has_docker or has_compose) else 0) + (10 if has_logging else 0),
        }

    def _dim_security(self) -> dict:
        has_eval = False
        eval_files = []
        for fp in list(Path(self.root).rglob("*.py"))[:200]:
            if _should_skip(str(fp)):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    c = f.read(16384)
                if "eval(" in c or "exec(" in c:
                    has_eval = True
                    eval_files.append(os.path.relpath(str(fp), self.root))
            except Exception:
                pass
        return {
            "has_eval_exec": has_eval,
            "eval_exec_files": eval_files[:5],
            "score": 20 if not has_eval else 5,
        }


def test_dimensions(root: str) -> dict:
    """便捷四维度测试"""
    return DimensionTester(root).test()