"""
guard.py — 行动前守卫系统
每次动手前强制全项目扫描，禁止跳过任何步骤
"""

import os, subprocess, re, hashlib, time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

class GuardStatus(Enum):
    PASS="pass"; BLOCK="block"; WARN="warn"

@dataclass
class FileScanItem:
    path: str; size: int; hash: str; ext: str
    issues: List[str] = field(default_factory=list)

@dataclass
class ScanSnapshot:
    root: str; time: str; total_files: int; total_size: int
    files: List[FileScanItem] = field(default_factory=list)
    issues_count: int=0; warnings_count: int=0

@dataclass
class GuardReport:
    status: GuardStatus = GuardStatus.PASS
    pre_scan: Optional[ScanSnapshot] = None
    post_scan: Optional[ScanSnapshot] = None
    framework_check: dict = field(default_factory=dict)
    diff_summary: str=""; block_reason: str=""; timestamp: str=""


# ── 危险模式检测 ──
DANGER_PATTERNS = [
    (r"API_KEY\s*=\s*['\"][^'\"]{20,}['\"]", "硬编码API密钥"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "硬编码密码"),
    (r"token\s*=\s*['\"][^'\"]{20,}['\"]", "硬编码Token"),
    (r"eval\s*\(.+\)", "危险eval"),
    (r"exec\s*\(.+\)", "危险exec"),
    (r"os\.system\s*\(.+\)", "危险system"),
    (r"subprocess\.(?:call|run|Popen)\s*\(.+shell\s*=\s*True", "危险shell=True"),
]

CODE_EXTS = {".py",".js",".ts",".jsx",".tsx",".vue",
             ".html",".css",".json",".yaml",".yml",
             ".md",".sh",".bat",".ps1",".java",".go",".rs"}

SKIP_DIRS = {".git","node_modules","__pycache__",".venv","venv",
             "dist","build",".next",".gbt","data",".idea",".vscode"}


class PreActionGuard:
    """行动前守卫 — 强制全项目扫描，禁止跳过任何文件"""

    def __init__(self, project_root: str, strict: bool = True):
        self.root = os.path.abspath(project_root)
        self.strict = strict
        self._pre: Optional[ScanSnapshot] = None
        self._blocked = False

    def full_scan(self) -> ScanSnapshot:
        """全项目扫描 — 每个文件必须检查"""
        print(f"\n🔍 全项目扫描: {self.root}")
        t0 = time.time()
        files = []; total_size = 0; issues = 0; warnings = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                ext = os.path.splitext(fname)[1].lower()
                try:
                    fsize = os.path.getsize(fpath); total_size += fsize
                    if ext in CODE_EXTS:
                        fhash = self._hash(fpath)
                        item = FileScanItem(path=os.path.relpath(fpath, self.root),
                            size=fsize, hash=fhash, ext=ext)
                        if ext in {".py",".js",".ts",".sh",".bat"}:
                            try:
                                with open(fpath,"r",encoding="utf-8",errors="ignore") as f:
                                    item.issues = self._detect(f.read())
                                if item.issues:
                                    issues += len(item.issues)
                                    for iss in item.issues:
                                        print(f"  ⚠️ {item.path}: {iss}")
                            except Exception:
                                pass  # 单个文件扫描异常不阻断全项目扫描
                        files.append(item)
                        if len(files) % 80 == 0: print(f"  📂 {len(files)}...")
                except Exception as e:
                    warnings += 1
        elapsed = time.time()-t0
        snap = ScanSnapshot(root=self.root, time=datetime.now().isoformat(),
            total_files=len(files), total_size=total_size, files=files,
            issues_count=issues, warnings_count=warnings)
        print(f"  ✅ {len(files)}文件/{self._fs(total_size)} | {issues}问题 | {elapsed:.1f}s")
        self._pre = snap
        return snap

    def pre_action_check(self, action: str) -> GuardReport:
        """行动前强制检查 — 不通过阻断"""
        print(f"\n🛡️ 行动前守卫: {action}")
        rpt = GuardReport(timestamp=datetime.now().isoformat())
        rpt.pre_scan = self.full_scan()
        rpt.framework_check = self._check_fw()
        if self.strict and rpt.pre_scan.issues_count > 0:
            rpt.status = GuardStatus.BLOCK
            rpt.block_reason = f"发现{rpt.pre_scan.issues_count}个安全隐患"
            self._blocked = True
            print(f"  🚫 阻断: {rpt.block_reason}")
        elif not rpt.framework_check.get("ok", True):
            rpt.status = GuardStatus.BLOCK
            rpt.block_reason = "框架不完整"
            self._blocked = True
            print(f"  🚫 阻断: {rpt.block_reason}")
        else:
            rpt.status = GuardStatus.PASS
            print(f"  ✅ 放行")
        return rpt

    def post_action_check(self, action: str) -> GuardReport:
        """行动后检查 — 对比变化"""
        print(f"\n🔍 行动后检查: {action}")
        rpt = GuardReport(timestamp=datetime.now().isoformat())
        rpt.post_scan = self.full_scan()
        if self._pre:
            pre_h = {f.path: f.hash for f in self._pre.files}
            post_h = {f.path: f.hash for f in rpt.post_scan.files}
            new = set(post_h)-set(pre_h)
            deleted = set(pre_h)-set(post_h)
            changed = {p for p in set(pre_h)&set(post_h) if pre_h[p]!=post_h[p]}
            parts = []
            if new: parts.append(f"+{len(new)}")
            if deleted: parts.append(f"-{len(deleted)}")
            if changed: parts.append(f"~{len(changed)}")
            rpt.diff_summary = ",".join(parts) if parts else "无变化"
            print(f"  差异: {rpt.diff_summary}")
            for f in sorted(changed)[:8]: print(f"    ~ {f}")
        rpt.status = GuardStatus.PASS
        return rpt

    def bidirectional_check(self, action: str) -> Tuple[GuardReport, GuardReport]:
        """双向检查: 行动前+行动后"""
        pre = self.pre_action_check(action)
        if pre.status == GuardStatus.BLOCK:
            return pre, GuardReport(status=GuardStatus.BLOCK, block_reason="前置未通过")
        return pre, self.post_action_check(action)

    def deploy_check(self) -> GuardReport:
        """部署前全面检查"""
        print(f"\n🚀 部署前检查...")
        rpt = GuardReport(timestamp=datetime.now().isoformat())
        rpt.pre_scan = self.full_scan()
        rpt.framework_check = self._check_fw()
        git_ok = self._check_git()
        if not git_ok:
            rpt.status = GuardStatus.WARN
            print("  ⚠️ Git未提交")
        if rpt.pre_scan.issues_count > 0:
            rpt.status = GuardStatus.BLOCK
            rpt.block_reason = f"安全问题:{rpt.pre_scan.issues_count}"
        elif not rpt.framework_check.get("ok"):
            rpt.status = GuardStatus.BLOCK
            rpt.block_reason = "框架不完整"
        else:
            rpt.status = GuardStatus.PASS
            print("  ✅ 部署通过")
        return rpt

    def _hash(self, path: str) -> str:
        try:
            h = hashlib.md5()
            with open(path,"rb") as f:
                for c in iter(lambda: f.read(8192), b""): h.update(c)
            return h.hexdigest()
        except Exception: return "err"

    def _detect(self, content: str) -> List[str]:
        return [f"🚨{desc}" for p, desc in DANGER_PATTERNS if re.search(p, content)]

    def _fs(self, s: int) -> str:
        for u in ["B","KB","MB","GB"]:
            if s < 1024: return f"{s:.1f}{u}"
            s /= 1024
        return f"{s:.1f}TB"

    def _check_fw(self) -> dict:
        """检测项目根目录下的核心框架文件 (self.root/gbt/)"""
        root = self.root
        req = ["gbt/__init__.py","gbt/llm.py","gbt/providers.py",
            "gbt/tool.py","gbt/agent.py","gbt/message.py","gbt/react.py",
            "gbt/memory.py","gbt/evolve.py","gbt/guard.py",
            "gbt/agents.py",
            "tools/__init__.py","tools/mcp_tools.py","main.py","requirements.txt"]
        errs = [rf for rf in req if not os.path.exists(os.path.join(root, rf))]
        ok = len(req)-len(errs)
        r = {"ok":not errs,"total":len(req),"found":ok,"missing":len(errs),"errors":errs}
        if errs:
            print(f"  ❌ 缺{len(errs)}文件")
            for e in errs: print(f"     - {e}")
        else:
            print(f"  ✅ 框架完整 {ok}/{len(req)}")
        return r

    def _check_git(self) -> bool:
        try:
            r = subprocess.run(["git","status","--porcelain"], shell=False,
                capture_output=True, text=True, timeout=10, cwd=self.root)
            dirty = len([l for l in r.stdout.split("\n") if l.strip()])
            if dirty: print(f"  📝 Git:{dirty}未提交"); return False
            print("  ✅ Git干净"); return True
        except Exception as e:
            print(f"  ⚠️ Git检查失败: {e}")
            return False  # 无法验证时保守处理

    @property
    def is_blocked(self) -> bool:
        return self._blocked


def scan_all(root: str) -> ScanSnapshot:
    return PreActionGuard(root, strict=False).full_scan()

def guard_action(root: str, action: str) -> GuardReport:
    return PreActionGuard(root).pre_action_check(action)

def guard_deploy(root: str) -> GuardReport:
    return PreActionGuard(root).deploy_check()