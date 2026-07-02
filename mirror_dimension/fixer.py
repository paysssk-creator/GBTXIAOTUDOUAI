# -*- coding: utf-8 -*-
"""沙盒修复引擎 — 镜像→扫描→修复→验证→部署"""
import os, re, shutil, tempfile
from datetime import datetime
from typing import List, Tuple

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".gbt", "data", "vendor",
    "venv_cradle", "venv_cradle_py310", "site-packages",
}

FIX_PATTERNS = [
    (re.compile(r"^(\s*)except\s*:\s*([#\s].*)?$", re.MULTILINE),
     r"\1except Exception as e:\2"),
    (re.compile(r"\bshell\s*=\s*True\b"), "shell=False"),
]


class SandboxFixer:
    """沙盒修复器: 在临时镜像中修复后部署回源"""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.root = os.path.abspath(project_root)
        self.dry_run = dry_run

    def run(self) -> dict:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mirror_dir = os.path.join(tempfile.gettempdir(), f"gbt_mirror_fix_{ts}")

        result = {
            "project": self.root, "mirror": mirror_dir,
            "files_scanned": 0, "fixes_applied": 0,
            "files_fixed": [], "syntax_errors": [],
            "dangers_reported": [], "deployed": 0,
            "dry_run": self.dry_run, "clean": False, "duration_s": 0,
        }

        try:
            shutil.copytree(
                self.root, mirror_dir,
                ignore=shutil.ignore_patterns(
                    ".git", "node_modules", "__pycache__", ".venv",
                    "venv", "dist", "build", ".gbt", "data",
                    "vendor", "venv_cradle", "venv_cradle_py310",
                    "site-packages"),
                dirs_exist_ok=True,
            )
            fix_count, fixed_files, dangers = self._scan_and_fix(mirror_dir)
            result["fixes_applied"] = fix_count
            result["files_fixed"] = fixed_files
            result["dangers_reported"] = dangers

            syntax_errs = self._verify_python_syntax(mirror_dir)
            result["syntax_errors"] = syntax_errs

            if not syntax_errs and fixed_files and not self.dry_run:
                deployed = 0
                for rel in fixed_files:
                    src = os.path.join(mirror_dir, rel)
                    dst = os.path.join(self.root, rel)
                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        deployed += 1
                    except Exception:
                        pass
                result["deployed"] = deployed

            result["clean"] = not syntax_errs and not dangers
        except Exception as e:
            result["error"] = str(e)
        finally:
            try:
                shutil.rmtree(mirror_dir, ignore_errors=True)
            except Exception:
                pass

        return result

    def _scan_and_fix(self, mirror_dir: str) -> Tuple[int, list, list]:
        fix_count, fixed_files, dangers = 0, [], []
        for dirpath, dirnames, filenames in os.walk(mirror_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        original = f.read()
                except Exception:
                    continue
                modified = original
                for pattern, replacement in FIX_PATTERNS:
                    modified = pattern.sub(replacement, modified)
                if modified != original:
                    try:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(modified)
                        fix_count += 1
                        fixed_files.append(os.path.relpath(fpath, mirror_dir))
                    except Exception:
                        pass
        return fix_count, fixed_files, dangers

    def _verify_python_syntax(self, mirror_dir: str) -> List[str]:
        errors = []
        for dirpath, dirnames, filenames in os.walk(mirror_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        compile(f.read(), fpath, "exec")
                except SyntaxError as e:
                    errors.append(
                        f"{os.path.relpath(fpath, mirror_dir)}:{e.lineno}: {e.msg}")
                except Exception:
                    pass
        return errors


def fix_project(root: str, dry_run: bool = False) -> dict:
    """便捷修复函数"""
    return SandboxFixer(root, dry_run=dry_run).run()
