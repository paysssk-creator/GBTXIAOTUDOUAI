# -*- coding: utf-8 -*-
"""
镜像多维度空间 — 独立CLI工具
================================
统一入口: scan / audit / fix / full / dimensions
纯Python原生,零外部JS依赖,所有操作在MirrorSpace沙盒中执行

用法:
  python mirror_dimension_cli.py scan <项目路径>
  python mirror_dimension_cli.py audit <项目路径>
  python mirror_dimension_cli.py fix <项目路径>
  python mirror_dimension_cli.py full <项目路径> [--dry-run]
  python mirror_dimension_cli.py report <report.json>

打包: pyinstaller mirror_dimension.spec → dist/GBT_MirrorDimension.exe
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── UTF-8 on Windows ────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── 尝试从 gbt 导入核心API,失败则用内置回退 ──────────────
_GUARD_AVAILABLE = False
_MIRROR_AVAILABLE = False

try:
    from gbt.guard import PreActionGuard, GuardReport, GuardStatus
    _GUARD_AVAILABLE = True
except ImportError:
    pass

try:
    from gbt.mirror import MirrorSpace, MirrorPipeline, RealCodeValidator, CodeIssue, IssueType
    _MIRROR_AVAILABLE = True
except ImportError:
    pass


# ══════════════════════════════════════════════════════════
#  内置回退检测模式 (当 gbt 模块不可用时)
# ══════════════════════════════════════════════════════════

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

# ── 危险模式 ──
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

# ── 虚假代码模式 ──
FAKE_PATTERNS = [
    (re.compile(r"#\s*TODO.*", re.I), "TODO_PLACEHOLDER"),
    (re.compile(r"#\s*FIXME.*", re.I), "FIXME_PLACEHOLDER"),
    (re.compile(r"#\s*HACK.*", re.I), "HACK_MARKER"),
    (re.compile(r"raise\s+NotImplementedError"), "NOT_IMPLEMENTED"),
    (re.compile(r"return\s+None\s*#.*TODO"), "STUB_RETURN_NONE"),
    (re.compile(r"return\s+\[\]\s*#.*TODO"), "STUB_RETURN_EMPTY"),
    (re.compile(r"return\s+\{\}\s*#.*TODO"), "STUB_RETURN_DICT"),
    (re.compile(r"=\s*['\"]test['\"]", re.I), "FAKE_TEST_DATA"),
    (re.compile(r"=\s*['\"]placeholder['\"]", re.I), "FAKE_PLACEHOLDER"),
    (re.compile(r"=\s*['\"]mock['\"]", re.I), "FAKE_MOCK"),
    (re.compile(r"=\s*['\"]dummy['\"]", re.I), "FAKE_DUMMY"),
    (re.compile(r"=\s*['\"]fake['\"]", re.I), "FAKE_FAKE"),
    (re.compile(r"=\s*['\"]xxx['\"]", re.I), "FAKE_XXX"),
]

# ── 自动修复模式 ──
FIX_PATTERNS = [
    (
        re.compile(r"^(\s*)except\s*:\s*([#\s].*)?$", re.MULTILINE),
        r"\1except Exception as e:\2",
        "bare except → Exception as e",
    ),
    (
        re.compile(r"\bshell\s*=\s*True\b"),
        "shell=False",
        "shell=True → shell=False",
    ),
]

SENSITIVE_FILE_PATTERNS = [
    ".env", ".pem", ".key", "credentials", "secret",
    ".db", ".sqlite", "password",
]

REQUIRED_GITIGNORE_RULES = [
    ".env", "*.db", "*.sqlite", "*.pem", "*.key",
    "__pycache__", "*.pyc", "data/",
]


# ══════════════════════════════════════════════════════════
#  扫描引擎
# ══════════════════════════════════════════════════════════

class ProjectScanner:
    """统一项目扫描器 — 危险 + 虚假 + 语法"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)
        self.dangers: List[dict] = []
        self.fakes: List[dict] = []
        self.syntax_errors: List[dict] = []
        self.total_files = 0

    def scan(self) -> dict:
        """执行全量扫描"""
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

                if ext == ".py":
                    self._check_syntax(fpath, rel)
                self._scan_file(fpath, rel)

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
            "clean": not (self.dangers or self.syntax_errors),
        }

    def _scan_file(self, fpath: str, rel: str) -> None:
        """扫描单个文件"""
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return

        for i, line in enumerate(content.split("\n"), 1):
            for pat, tag in DANGER_PATTERNS:
                m = pat.search(line) if "MULTILINE" not in str(pat.flags) else None
                if m or (pat.search(content)):
                    self.dangers.append({
                        "file": rel, "line": i,
                        "type": tag,
                        "snippet": line.strip()[:120],
                    })
                    break

            for pat, tag in FAKE_PATTERNS:
                if pat.search(line):
                    self.fakes.append({
                        "file": rel, "line": i,
                        "type": tag,
                        "snippet": line.strip()[:120],
                    })
                    break

    def _check_syntax(self, fpath: str, rel: str) -> None:
        """Python 语法检查"""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                compile(f.read(), fpath, "exec")
        except SyntaxError as e:
            self.syntax_errors.append({
                "file": rel,
                "line": e.lineno or 0,
                "type": "SYNTAX_ERROR",
                "snippet": str(e),
            })
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  审计引擎
# ══════════════════════════════════════════════════════════

class ProjectAuditor:
    """深度审计 — 密钥/敏感文件/.gitignore/配置"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)

    def audit(self) -> dict:
        t0 = time.time()
        results = {
            "project": self.root,
            "sensitive_files": self._check_sensitive(),
            "gitignore_gaps": self._check_gitignore(),
            "untracked_risks": self._check_untracked(),
            "config_status": self._check_config(),
            "duration_s": 0,
        }
        all_ok = (
            not results["sensitive_files"]
            and not results["gitignore_gaps"]
            and not results["untracked_risks"]
        )
        results["clean"] = all_ok
        results["duration_s"] = round(time.time() - t0, 2)
        return results

    def _check_sensitive(self) -> List[str]:
        """检查敏感文件"""
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                for pat in SENSITIVE_FILE_PATTERNS:
                    if pat in fname.lower():
                        rel = os.path.relpath(
                            os.path.join(dirpath, fname), self.root
                        )
                        found.append(rel)
                        break
        return found

    def _check_gitignore(self) -> List[str]:
        """检查 .gitignore 缺失的规则"""
        gi = os.path.join(self.root, ".gitignore")
        if not os.path.exists(gi):
            return ["NO_GITIGNORE_FILE"]
        with open(gi, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [r for r in REQUIRED_GITIGNORE_RULES if r not in content]

    def _check_untracked(self) -> List[str]:
        """检查未跟踪的敏感文件"""
        try:
            r = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.root, capture_output=True, text=True, timeout=15,
            )
            untracked = r.stdout.strip().split("\n") if r.stdout.strip() else []
        except Exception:
            return []
        return [f for f in untracked
                if any(p in f.lower() for p in SENSITIVE_FILE_PATTERNS)]

    def _check_config(self) -> dict:
        """检查配置文件完整性"""
        cfgs = {}
        for name in [".env.example", "pyproject.toml", "requirements.txt"]:
            cfgs[name] = os.path.exists(os.path.join(self.root, name))
        return cfgs


# ══════════════════════════════════════════════════════════
#  镜像沙盒修复
# ══════════════════════════════════════════════════════════

class SandboxFixer:
    """在镜像沙盒中扫描→修复→验证→部署"""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.root = os.path.abspath(project_root)
        self.dry_run = dry_run

    def run(self) -> dict:
        t0 = time.time()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mirror_dir = os.path.join(
            tempfile.gettempdir(), f"gbt_mirror_fix_{ts}"
        )

        result = {
            "project": self.root,
            "mirror": mirror_dir,
            "files_scanned": 0,
            "fixes_applied": 0,
            "files_fixed": [],
            "syntax_errors": [],
            "dangers_reported": [],
            "deployed": False,
            "dry_run": self.dry_run,
            "clean": False,
            "duration_s": 0,
        }

        try:
            # 1. 创建镜像
            shutil.copytree(
                self.root, mirror_dir,
                ignore=shutil.ignore_patterns(
                    ".git", "node_modules", "__pycache__", ".venv",
                    "venv", "dist", "build", ".gbt", "data",
                    "vendor", "venv_cradle", "venv_cradle_py310",
                    "site-packages", "__pycache__",
                ),
                dirs_exist_ok=True,
            )

            # 2. 扫描+修复
            fix_count, fixed_files, dangers = self._scan_and_fix(mirror_dir)
            result["fixes_applied"] = fix_count
            result["files_fixed"] = fixed_files
            result["dangers_reported"] = dangers

            # 3. 语法验证
            syntax_errs = self._verify_python_syntax(mirror_dir)
            result["syntax_errors"] = syntax_errs

            # 4. 部署 (语法无错 + 非dry-run)
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
            elif self.dry_run:
                result["deployed"] = "DRY_RUN_SKIPPED"

            result["clean"] = (
                not syntax_errs
                and not dangers
                and (not fixed_files or result["deployed"])
            )

        except Exception as e:
            result["error"] = str(e)
        finally:
            # 清理镜像
            try:
                shutil.rmtree(mirror_dir, ignore_errors=True)
            except Exception:
                pass

        result["duration_s"] = round(time.time() - t0, 2)
        return result

    def _scan_and_fix(self, mirror_dir: str) -> Tuple[int, list, list]:
        fix_count = 0
        fixed_files = []
        dangers = []

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
                file_fixes = 0

                for pattern, replacement, _desc in FIX_PATTERNS:
                    new_text = pattern.sub(replacement, modified)
                    if new_text != modified:
                        file_fixes += 1
                        modified = new_text

                if modified != original:
                    try:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(modified)
                        fix_count += file_fixes
                        fixed_files.append(
                            os.path.relpath(fpath, mirror_dir)
                        )
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
                        f"{os.path.relpath(fpath, mirror_dir)}:{e.lineno}: {e.msg}"
                    )
                except Exception:
                    pass
        return errors


# ══════════════════════════════════════════════════════════
#  四维度测试
# ══════════════════════════════════════════════════════════

class DimensionTester:
    """四维度测试: 用户/开发者/运维/安全"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)

    def test(self) -> dict:
        t0 = time.time()
        return {
            "project": self.root,
            "user": self._dim_user(),
            "developer": self._dim_developer(),
            "ops": self._dim_ops(),
            "security": self._dim_security(),
            "duration_s": round(time.time() - t0, 2),
            "verdict": self._verdict(),
        }

    def _dim_user(self) -> dict:
        """用户视角: 入口/文档/CLI"""
        checks = {}
        # 入口存在性
        entries = ["main.py", "entry.py", "agent_entry.py", "app/__init__.py"]
        checks["entries"] = {
            e: os.path.exists(os.path.join(self.root, e)) for e in entries
        }
        # README
        readme = os.path.join(self.root, "README.md")
        checks["has_readme"] = os.path.exists(readme)
        if checks["has_readme"]:
            try:
                with open(readme, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                checks["readme_size_kb"] = round(len(content) / 1024, 1)
            except Exception:
                checks["readme_size_kb"] = 0
        score = (
            (10 if any(checks["entries"].values()) else 0)
            + (10 if checks["has_readme"] else 0)
        )
        checks["score"] = min(score, 20)
        return checks

    def _dim_developer(self) -> dict:
        """开发者视角: 代码质量"""
        checks = {}
        py_files = list(Path(self.root).rglob("*.py"))
        py_files = [
            f for f in py_files
            if not any(s in str(f) for s in SKIP_DIRS)
        ]
        checks["python_file_count"] = len(py_files)

        # 检查 docstring 覆盖率
        with_doc = 0
        for fp in py_files[:200]:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                if '"""' in first_line or "'''" in first_line:
                    with_doc += 1
            except Exception:
                pass
        checks["docstring_rate"] = (
            round(with_doc / len(py_files[:200]) * 100, 1)
            if py_files else 0
        )
        score = min(round(checks["docstring_rate"] / 5), 20)
        checks["score"] = score
        return checks

    def _dim_ops(self) -> dict:
        """运维视角: Docker/日志/健康检查"""
        checks = {}
        checks["has_dockerfile"] = os.path.exists(
            os.path.join(self.root, "Dockerfile")
        )
        checks["has_docker_compose"] = os.path.exists(
            os.path.join(self.root, "docker-compose.yml")
        )
        # 检查 logging 使用
        has_logging = False
        for fp in Path(self.root).rglob("*.py"):
            if any(s in str(fp) for s in SKIP_DIRS):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    if "import logging" in f.read(4096):
                        has_logging = True
                        break
            except Exception:
                pass
        checks["uses_logging"] = has_logging
        score = (
            (10 if checks["has_dockerfile"] or checks["has_docker_compose"] else 0)
            + (10 if has_logging else 0)
        )
        checks["score"] = score
        return checks

    def _dim_security(self) -> dict:
        """安全视角"""
        checks = {}
        # 检查 eval/exec 使用
        has_eval = False
        for fp in Path(self.root).rglob("*.py"):
            if any(s in str(fp) for s in SKIP_DIRS):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(32768)
                if "eval(" in content or "exec(" in content:
                    has_eval = True
                    checks.setdefault("eval_exec_files", []).append(
                        os.path.relpath(str(fp), self.root)
                    )
            except Exception:
                pass
        checks["has_eval_exec"] = has_eval
        score = 20 if not has_eval else 5
        checks["score"] = score
        return checks

    def _verdict(self) -> str:
        # called after all dimensions populated
        return "PENDING"


# ══════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════

def cmd_scan(args) -> int:
    """扫描模式: 全量扫描危险代码 + 虚假代码 + 语法错误"""
    print(f"\n{'=' * 60}")
    print(f"  🔍 镜像空间全量扫描")
    print(f"  项目: {args.path}")
    print(f"{'=' * 60}\n")

    scanner = ProjectScanner(args.path)
    result = scanner.scan()

    _print_scan_result(result)
    _maybe_save(result, args.output)
    return 0 if result["clean"] else 1


def cmd_audit(args) -> int:
    """审计模式: 深度审计"""
    print(f"\n{'=' * 60}")
    print(f"  🔐 深度安全审计")
    print(f"  项目: {args.path}")
    print(f"{'=' * 60}\n")

    auditor = ProjectAuditor(args.path)
    result = auditor.audit()

    print(f"  敏感文件: {len(result['sensitive_files'])}")
    for f in result["sensitive_files"]:
        print(f"    ⚠️  {f}")

    print(f"  .gitignore 缺口: {len(result['gitignore_gaps'])}")
    for g in result["gitignore_gaps"]:
        print(f"    ❌ {g}")

    print(f"  未跟踪敏感文件: {len(result['untracked_risks'])}")
    for u in result["untracked_risks"]:
        print(f"    ⚠️  {u}")

    print(f"  配置文件:")
    for k, v in result["config_status"].items():
        print(f"    {'✅' if v else '❌'} {k}")

    print(f"\n  {'✅ 审计通过' if result['clean'] else '⚠️  发现问题'}")
    _maybe_save(result, args.output)
    return 0 if result["clean"] else 1


def cmd_fix(args) -> int:
    """修复模式: 沙盒修复"""
    print(f"\n{'=' * 60}")
    print(f"  🔧 镜像沙盒修复{' [DRY-RUN]' if args.dry_run else ''}")
    print(f"  项目: {args.path}")
    print(f"{'=' * 60}\n")

    fixer = SandboxFixer(args.path, dry_run=args.dry_run)
    result = fixer.run()

    print(f"  扫描文件: {result['files_scanned']}")
    print(f"  已修复: {result['fixes_applied']} 处")
    print(f"  涉及文件: {len(result['files_fixed'])}")
    for f in result["files_fixed"]:
        print(f"    🔧 {f}")

    if result["syntax_errors"]:
        print(f"  ❌ 语法错误: {len(result['syntax_errors'])}")
        for e in result["syntax_errors"][:10]:
            print(f"    {e}")

    if result["dangers_reported"]:
        print(f"  ⚠️  需人工审查: {len(result['dangers_reported'])}")
        for d in result["dangers_reported"][:10]:
            print(f"    {d}")

    status = (
        "DRY-RUN 完成" if args.dry_run
        else f"部署 {result.get('deployed', 0)} 文件" if result["deployed"]
        else "无变更"
    )
    print(f"\n  {'✅' if result['clean'] else '⚠️'}  {status}")
    _maybe_save(result, args.output)
    return 0 if result["clean"] else 1


def cmd_full(args) -> int:
    """完整管道: scan → audit → fix → dimensions"""
    print(f"\n{'=' * 60}")
    print(f"  🪞 镜像多维度空间 — 完整管道")
    print(f"  项目: {args.path}")
    print(f"  {'[DRY-RUN]' if args.dry_run else '[实跑模式]'}")
    print(f"{'=' * 60}")

    exit_code = 0
    report = {
        "project": os.path.abspath(args.path),
        "timestamp": datetime.now().isoformat(),
        "stages": {},
    }

    # Stage 1: Scan
    print(f"\n── Stage 1/4: 全量扫描 ──")
    scanner = ProjectScanner(args.path)
    report["stages"]["scan"] = scanner.scan()
    _print_scan_result(report["stages"]["scan"])
    if not report["stages"]["scan"]["clean"]:
        exit_code = 1

    # Stage 2: Audit
    print(f"\n── Stage 2/4: 深度审计 ──")
    auditor = ProjectAuditor(args.path)
    report["stages"]["audit"] = auditor.audit()
    if not report["stages"]["audit"]["clean"]:
        exit_code = max(exit_code, 1)

    # Stage 3: Fix
    print(f"\n── Stage 3/4: 沙盒修复 ──")
    fixer = SandboxFixer(args.path, dry_run=args.dry_run)
    report["stages"]["fix"] = fixer.run()
    if not report["stages"]["fix"]["clean"]:
        exit_code = max(exit_code, 1)

    # Stage 4: Dimensions
    print(f"\n── Stage 4/4: 四维度测试 ──")
    tester = DimensionTester(args.path)
    dims = tester.test()
    report["stages"]["dimensions"] = dims
    _print_dimension_result(dims)
    scores = [d.get("score", 0) for d in [dims["user"], dims["developer"], dims["ops"], dims["security"]]]
    avg = sum(scores) / len(scores) if scores else 0
    dims["verdict"] = "PASS" if avg >= 60 else "WARN" if avg >= 40 else "FAIL"

    # Summary
    total_duration = sum(
        s.get("duration_s", 0)
        for s in report["stages"].values()
        if isinstance(s, dict)
    )
    report["total_duration_s"] = round(total_duration, 2)
    report["exit_code"] = exit_code

    print(f"\n{'=' * 60}")
    print(f"  🪞 管道完成 — 总耗时 {total_duration:.1f}s")
    stages_ok = sum(
        1 for s in report["stages"].values()
        if isinstance(s, dict) and s.get("clean", True)
    )
    print(f"  通过: {stages_ok}/4 阶段")
    print(f"  四维度平均分: {avg:.0f}/80")
    print(f"{'=' * 60}\n")

    _maybe_save(report, args.output)
    return exit_code


def cmd_dimensions(args) -> int:
    """四维度测试模式"""
    print(f"\n{'=' * 60}")
    print(f"  🎯 四维度测试")
    print(f"  项目: {args.path}")
    print(f"{'=' * 60}\n")

    tester = DimensionTester(args.path)
    result = tester.test()
    _print_dimension_result(result)
    _maybe_save(result, args.output)
    return 0


def _print_scan_result(result: dict) -> None:
    """打印扫描结果"""
    print(f"  扫描文件: {result['total_files']}")
    print(f"  安全隐患: {result['dangers']}")
    for d in result.get("danger_items", [])[:15]:
        print(f"    🚨 [{d['type']}] {d['file']}:{d['line']}")
    if result["dangers"] > 15:
        print(f"    ... 还有 {result['dangers'] - 15} 条")

    print(f"  虚假代码: {result['fakes']}")
    for f in result.get("fake_items", [])[:10]:
        print(f"    📌 [{f['type']}] {f['file']}:{f['line']}")
    if result["fakes"] > 10:
        print(f"    ... 还有 {result['fakes'] - 10} 条")

    if result["syntax_errors"]:
        print(f"  ❌ 语法错误: {result['syntax_errors']}")
        for s in result.get("syntax_items", [])[:5]:
            print(f"    {s['file']}:{s['line']} — {s['snippet']}")


def _print_dimension_result(dims: dict) -> None:
    """打印四维度测试结果"""
    labels = {"user": "用户视角", "developer": "开发者视角",
              "ops": "运维视角", "security": "安全视角"}
    for key in ["user", "developer", "ops", "security"]:
        d = dims.get(key, {})
        score = d.get("score", 0)
        icon = "✅" if score >= 15 else "⚠️" if score >= 10 else "❌"
        print(f"  {icon} {labels[key]}: {score}/20")


def _maybe_save(data: dict, path: Optional[str]) -> None:
    """保存 JSON 报告"""
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  📄 报告已保存: {path}")
    except Exception as e:
        print(f"\n  ⚠️ 保存失败: {e}")


# ══════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="GBT_MirrorDimension",
        description="镜像多维度空间 — 项目安全验证 & 沙盒修复工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="全量扫描 (危险代码+虚假代码+语法)")
    p_scan.add_argument("path", help="项目路径")
    p_scan.add_argument("-o", "--output", help="JSON报告输出路径")

    # audit
    p_audit = sub.add_parser("audit", help="深度审计 (密钥/敏感文件/.gitignore)")
    p_audit.add_argument("path", help="项目路径")
    p_audit.add_argument("-o", "--output", help="JSON报告输出路径")

    # fix
    p_fix = sub.add_parser("fix", help="沙盒自动修复")
    p_fix.add_argument("path", help="项目路径")
    p_fix.add_argument("--dry-run", action="store_true", help="仅分析不写入")
    p_fix.add_argument("-o", "--output", help="JSON报告输出路径")

    # full
    p_full = sub.add_parser("full", help="完整管道 (scan→audit→fix→dimensions)")
    p_full.add_argument("path", help="项目路径")
    p_full.add_argument("--dry-run", action="store_true", help="仅分析不写入")
    p_full.add_argument("-o", "--output", help="JSON报告输出路径")

    # dimensions
    p_dim = sub.add_parser("dimensions", help="四维度测试")
    p_dim.add_argument("path", help="项目路径")
    p_dim.add_argument("-o", "--output", help="JSON报告输出路径")

    args = parser.parse_args()
    handlers = {
        "scan": cmd_scan,
        "audit": cmd_audit,
        "fix": cmd_fix,
        "full": cmd_full,
        "dimensions": cmd_dimensions,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
