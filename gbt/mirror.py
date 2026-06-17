"""
mirror.py — 镜像空间系统
扫描→排除→规划→真实代码替换→镜像执行→验证→部署
拒绝虚假/占位/虚拟代码，只允许真实生产代码
"""

import os, re, shutil, subprocess, json, time, tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum


class MirrorStage(Enum):
    SCAN="scan"; CLASSIFY="classify"; PLAN="plan"
    MIRROR="mirror"; VERIFY="verify"; DEPLOY="deploy"


class IssueType(Enum):
    PLACEHOLDER="placeholder"     # 占位符
    STUB="stub"                   # 空函数/假实现
    FAKE="fake"                   # 虚假数据
    HARDCODE="hardcode"           # 硬编码
    MISSING="missing"             # 缺失实现
    UNSAFE="unsafe"               # 不安全代码


@dataclass
class CodeIssue:
    file: str; line: int; issue_type: IssueType
    snippet: str; description: str; fix_plan: str = ""

@dataclass
class FixPlan:
    issue: CodeIssue
    target_file: str
    replacement: str  # 真实生产代码
    test: str = ""    # 验证测试

@dataclass
class MirrorReport:
    stage: MirrorStage; status: str; details: str = ""
    issues_found: int=0; issues_fixed: int=0
    placeholder_count: int=0; fake_count: int=0
    duration: float=0.0


# ── 虚假/占位代码检测模式 ──
PLACEHOLDER_PATTERNS = [
    # 占位符注释
    (r"#\s*TODO.*", IssueType.PLACEHOLDER, "TODO占位"),
    (r"#\s*FIXME.*", IssueType.PLACEHOLDER, "FIXME占位"),
    (r"#\s*HACK.*", IssueType.PLACEHOLDER, "HACK标注"),
    (r"#\s*XXX.*", IssueType.PLACEHOLDER, "XXX标注"),
    (r"//\s*TODO.*", IssueType.PLACEHOLDER, "TODO占位"),
    (r"//\s*FIXME.*", IssueType.PLACEHOLDER, "FIXME占位"),
    # 虚假返回值
    (r"return\s+None\s*#.*TODO", IssueType.STUB, "空返回+TODO"),
    (r"return\s+\"\"\s*#.*TODO", IssueType.STUB, "空字符串+TODO"),
    (r"return\s+\[\]\s*#.*TODO", IssueType.STUB, "空列表+TODO"),
    (r"return\s+\{\}\s*#.*TODO", IssueType.STUB, "空字典+TODO"),
    (r"return\s+True\s*#.*TODO", IssueType.STUB, "硬编码True+TODO"),
    # 假实现
    (r"pass\s*#.*TODO", IssueType.STUB, "pass+TODO"),
    (r"raise\s+NotImplementedError", IssueType.STUB, "NotImplemented"),
    (r"NotImplemented", IssueType.STUB, "NotImplemented标记"),
    # 虚假数据
    (r"=\s*['\"]test['\"]", IssueType.FAKE, "测试假数据"),
    (r"=\s*['\"]placeholder['\"]", IssueType.FAKE, "占位假数据"),
    (r"=\s*['\"]mock['\"]", IssueType.FAKE, "mock假数据"),
    (r"=\s*['\"]dummy['\"]", IssueType.FAKE, "dummy假数据"),
    (r"=\s*['\"]fake['\"]", IssueType.FAKE, "fake假数据"),
    (r"=\s*['\"]sample['\"]", IssueType.FAKE, "sample假数据"),
    (r"=\s*['\"]example['\"]", IssueType.FAKE, "example假数据"),
    (r"=\s*['\"]your_.*['\"]", IssueType.FAKE, "your_xxx模板数据"),
    (r"=\s*['\"]xxx['\"]", IssueType.FAKE, "xxx假数据"),
    # 硬编码密钥(安全)
    (r"=\s*['\"][A-Za-z0-9+/]{32,}['\"]", IssueType.HARDCODE, "疑似硬编码密钥"),
    # 缺失的函数体
    (r"def\s+\w+\(.*\):\s*\n\s*pass\s*$", IssueType.MISSING, "空函数体"),
]

# 真实代码要求模式 (必须存在)
REAL_CODE_PATTERNS = [
    r"def\s+\w+\(.*\):\s*\n\s+.+",  # 函数有实际内容
    r"return\s+(?!None|True|False|\[\]|\{\}|\"\")",  # return真实值
]


class RealCodeValidator:
    """真实代码验证器 — 拒绝虚假/占位/虚拟代码"""

    def scan_file(self, filepath: str) -> List[CodeIssue]:
        """扫描单个文件的虚假代码问题"""
        issues = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                for pattern, issue_type, desc in PLACEHOLDER_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(CodeIssue(
                            file=filepath, line=i, issue_type=issue_type,
                            snippet=line.strip()[:100],
                            description=desc))
                        break  # 每行只匹配第一个模式
        except Exception as e:
            issues.append(CodeIssue(file=filepath, line=0,
                issue_type=IssueType.MISSING,
                snippet="", description=f"无法读取: {e}"))
        return issues

    def scan_project(self, root: str) -> List[CodeIssue]:
        """扫描整个项目的虚假代码"""
        all_issues = []
        skip = {".git","node_modules","__pycache__",".venv","venv",
                "dist","build",".gbt","data","__init__.py"}
        exts = {".py",".js",".ts"}

        print(f"\n🔍 虚假代码扫描: {root}")
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in exts: continue
                fpath = os.path.join(dirpath, fname)
                issues = self.scan_file(fpath)
                if issues:
                    all_issues.extend(issues)
                    for iss in issues:
                        tag = {"placeholder":"📌","stub":"🪫","fake":"🎭",
                               "hardcode":"🔑","missing":"🕳️","unsafe":"⚠️"}
                        print(f"  {tag.get(iss.issue_type.value,'•')} "
                              f"{os.path.relpath(fpath,root)}:{iss.line} {iss.description}")

        # 统计
        counts = {}
        for iss in all_issues:
            t = iss.issue_type.value
            counts[t] = counts.get(t, 0) + 1

        print(f"\n  📊 虚假代码统计: {len(all_issues)}个问题")
        for t, c in sorted(counts.items()):
            print(f"     {t}: {c}")
        if not all_issues:
            print("  ✅ 未发现虚假代码")
        return all_issues

    def is_fake_free(self, root: str) -> Tuple[bool, int]:
        """检查项目是否无虚假代码"""
        issues = self.scan_project(root)
        return len(issues) == 0, len(issues)


class MirrorSpace:
    """镜像空间 — 沙盒，所有变更先在此跑通再部署"""

    def __init__(self, source_root: str):
        self.source = os.path.abspath(source_root)
        self.mirror_dir = os.path.join(tempfile.gettempdir(),
            f"gbt_mirror_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self._active = False
        self._validator = RealCodeValidator()

    def __enter__(self):
        print(f"\n🪞 进入镜像空间...")
        skip = {".git","node_modules","__pycache__",".venv","venv",
                "dist","build",".gbt","data"}
        try:
            shutil.copytree(self.source, self.mirror_dir,
                ignore=shutil.ignore_patterns(*skip), dirs_exist_ok=True)
            self._active = True
            print(f"  ✅ 镜像就绪: {self.mirror_dir}")
        except Exception as e:
            print(f"  ❌ 失败: {e}"); raise
        return self

    def __exit__(self, *args):
        if self._active:
            try: shutil.rmtree(self.mirror_dir, ignore_errors=True)
            except: pass
        print("  🧹 镜像已清理")

    def get_path(self, rel: str) -> str:
        return os.path.join(self.mirror_dir, rel)

    def write_file(self, rel: str, content: str) -> str:
        fpath = self.get_path(rel)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        return fpath

    def run_test(self, cmd: str) -> Tuple[bool, str]:
        print(f"  🧪 镜像测试: {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                text=True, timeout=60, cwd=self.mirror_dir)
            ok = r.returncode == 0
            out = r.stdout.strip() or r.stderr.strip()
            print(f"  {'✅通过' if ok else '❌失败'}")
            return ok, out
        except subprocess.TimeoutExpired:
            return False, "⏱️超时"
        except Exception as e:
            return False, str(e)

    def verify_no_fakes(self) -> Tuple[bool, List[CodeIssue]]:
        issues = self._validator.scan_project(self.mirror_dir)
        return len(issues) == 0, issues

    def promote_to_source(self, rel: str) -> bool:
        src = self.get_path(rel)
        dst = os.path.join(self.source, rel)
        if not os.path.exists(src): return False
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  🚀 已部署: {rel}")
            return True
        except Exception as e:
            print(f"  ❌ 部署失败: {rel}: {e}")
            return False

    def promote_all(self) -> int:
        count = 0
        for root, dirs, files in os.walk(self.mirror_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), self.mirror_dir)
                if self.promote_to_source(rel): count += 1
        print(f"  🚀 批量部署: {count}文件")
        return count


class MirrorPipeline:
    """镜像流水线: 扫描→分类→规划→镜像→验证→部署"""

    def __init__(self, project_root: str):
        self.root = os.path.abspath(project_root)
        self.validator = RealCodeValidator()
        self.reports: List[MirrorReport] = []

    def run(self, fix_callback: Optional[Callable] = None) -> List[MirrorReport]:
        print(f"\n{'='*60}\n  🪞 镜像流水线\n{'='*60}")

        # Stage 1: 扫描虚假代码
        t0 = time.time()
        issues = self.validator.scan_project(self.root)
        r = MirrorReport(stage=MirrorStage.SCAN, status="ok",
            details=f"发现{len(issues)}问题",
            issues_found=len(issues),
            placeholder_count=sum(1 for i in issues if i.issue_type==IssueType.PLACEHOLDER),
            fake_count=sum(1 for i in issues if i.issue_type==IssueType.FAKE),
            duration=time.time()-t0)
        self.reports.append(r)

        if not issues:
            print("  ✅ 无虚假代码")
            self.reports.append(MirrorReport(stage=MirrorStage.DEPLOY, status="ok",
                details="项目干净", duration=0))
            return self.reports

        # Stage 2: 分类
        counts = {}
        for iss in issues:
            t = iss.issue_type.value
            counts[t] = counts.get(t, 0) + 1
        print(f"  📊 分类: {counts}")
        self.reports.append(MirrorReport(stage=MirrorStage.CLASSIFY,
            status="ok", details=str(counts)))

        # Stage 3-6: 镜像执行
        if fix_callback:
            try:
                with MirrorSpace(self.root) as mirror:
                    fixed = fix_callback(mirror, issues)
                    ok, remaining = mirror.verify_no_fakes()
                    fixed_count = len(issues) - len(remaining)

                    self.reports.append(MirrorReport(stage=MirrorStage.MIRROR,
                        status="ok" if ok else "fail",
                        details=f"修复{fixed_count}, 剩余{len(remaining)}"))

                    self.reports.append(MirrorReport(stage=MirrorStage.VERIFY,
                        status="ok" if ok else "fail",
                        details=f"{'无' if ok else len(remaining)}虚假代码"))

                    if ok:
                        count = mirror.promote_all()
                        self.reports.append(MirrorReport(stage=MirrorStage.DEPLOY,
                            status="ok", details=f"部署{count}文件",
                            issues_fixed=fixed_count))
                    else:
                        self.reports.append(MirrorReport(stage=MirrorStage.DEPLOY,
                            status="fail", details="❌ 拒绝部署: 仍有虚假代码"))
            except Exception as e:
                self.reports.append(MirrorReport(stage=MirrorStage.MIRROR,
                    status="fail", details=str(e)))
        else:
            self.reports.append(MirrorReport(stage=MirrorStage.MIRROR,
                status="skip", details="无修复回调"))

        # 打印总结
        print(f"\n{'='*60}")
        for rp in self.reports:
            ic = {"ok":"✅","fail":"❌","skip":"⏭️"}.get(rp.status,"•")
            print(f"  {ic} {rp.stage.value}: {rp.details}")
        print(f"{'='*60}\n")
        return self.reports


def scan_fakes(root: str) -> List[CodeIssue]:
    return RealCodeValidator().scan_project(root)

def mirror_run(root: str, callback: Callable) -> List[MirrorReport]:
    return MirrorPipeline(root).run(fix_callback=callback)

