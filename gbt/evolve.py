"""
evolve.py — 6步自进化闭环引擎
自查→扫描→备份→修复→审查→进化

每步均提供 Python 原生回退，不依赖外部 JS 文件。
所有异常均使用 `except Exception as e`，无裸 except。
"""

import os
import re
import subprocess
import time
import shlex
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .guard import PreActionGuard  # 行动前守卫


# ── 数据结构 ────────────────────────────────────────────

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class EvolveStep:
    name: str
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    duration: float = 0.0


@dataclass
class EvolveReport:
    project: str
    started: str
    finished: str = ""
    steps: List[EvolveStep] = field(default_factory=list)
    success: bool = False
    rollback: bool = False
    summary: str = ""


class EvolveAbort(Exception):
    """进化流程中止异常"""
    pass


# ── Step 4 自动修复模式 ─────────────────────────────────

# 每个模式: (正则, 替换, 描述, 是否可自动修复)
AUTO_FIX_PATTERNS = [
    # subprocess shell=False → shell=False
    (
        re.compile(r'\bshell\s*=\s*True\b'),
        'shell=False',
        'shell=False→shell=False',
        True,
    ),
    # 裸 except: → except Exception as e:
    (
        re.compile(r'^(\s*)except\s*:\s*([#\s].*)?$', re.MULTILINE),
        r'\1except Exception as e:\2',
        'bare except→Exception',
        True,
    ),
]

# 危险但无法自动修复的模式 (仅报告)
DANGER_PATTERNS_REPORT = [
    (re.compile(r'\bos\.system\s*\('), '危险 os.system() 调用'),
    (re.compile(r'\beval\s*\('), '危险 eval() 调用'),
    (re.compile(r'\bexec\s*\('), '危险 exec() 调用'),
    (re.compile(r'\b__import__\s*\('), '动态 __import__() 调用'),
]


# ── 引擎主体 ─────────────────────────────────────────────

class EvolveEngine:
    """6步自进化闭环引擎

    用法:
        engine = EvolveEngine("/path/to/project", dry_run=False)
        report = engine.run("描述此次进化")
    """

    def __init__(
        self,
        project_root: str,
        dry_run: bool = False,
        strong: bool = False,
        log_dir: Optional[str] = None,
    ):
        self.p = os.path.abspath(project_root)
        self.dry = dry_run
        self.strong = strong
        self.log_dir = log_dir or os.path.join(self.p, ".gbt", "evolve-logs")
        self.cline = os.path.join(os.path.expanduser("~"), ".cline")
        self.rpt: Optional[EvolveReport] = None
        self._backup_commit = ""

    # ── 主流程 ───────────────────────────────────────

    def run(self, desc: str = "") -> EvolveReport:
        """执行完整6步进化闭环"""
        self.rpt = EvolveReport(
            project=self.p,
            started=datetime.now().isoformat(),
        )
        os.makedirs(self.log_dir, exist_ok=True)

        banner = (
            f"\n{'=' * 50}\n"
            f"  🧬 6步闭环 — {self.p}\n"
            f"  {'🏃 DRY-RUN (仅分析不写入)' if self.dry else '💪 实跑模式'}\n"
            f"{'=' * 50}\n"
        )
        print(banner)

        try:
            self._s1()  # 自查
            self._s2()  # 扫描
            self._s3()  # 备份
            self._s4()  # 修复
            self._s5()  # 审查
            self._s6(desc)  # 进化
            self.rpt.success = True
        except EvolveAbort as e:
            self.rpt.summary = f"中止: {e}"
            self._rollback()
        except Exception as e:
            self.rpt.summary = f"异常: {e}"
            self._rollback()

        self.rpt.finished = datetime.now().isoformat()
        self._save()
        self._summary()
        return self.rpt

    # ── Step 1: 自查 ─────────────────────────────────

    def _s1(self) -> None:
        """Step1 — 强制全项目扫描，零跳过"""
        s = EvolveStep(name="Step1-自查")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("🔍 Step1 强制全项目扫描(零跳过)")

        try:
            guard = PreActionGuard(self.p, strict=self.strong)
            snapshot = guard.full_scan()
            s.output = (
                f"全扫描完成: {snapshot.total_files}文件/"
                f"{self._fs(snapshot.total_size)} | "
                f"{snapshot.issues_count}问题"
            )
            s.status = StepStatus.OK
            print(f"  ✅ {s.output}")

            if guard.is_blocked and self.strong:
                raise EvolveAbort(f"安全隐患: {snapshot.issues_count}个")
        except EvolveAbort:
            raise
        except Exception as e:
            s.status = StepStatus.FAIL
            s.error = str(e)
            print(f"  ❌ Step1 失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── Step 2: 发现问题 ─────────────────────────────

    def _s2(self) -> None:
        """Step2 — 代码扫描；JS 不可用时回退到 Python guard.full_scan()"""
        s = EvolveStep(name="Step2-扫描")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("🔎 Step2 代码扫描")

        if self._tool("scanner.js"):
            # 优先使用 scanner.js
            try:
                r = self._node("scanner.js", f'--project "{self.p}"')
                s.output = r[:800]
                s.status = StepStatus.OK
                print("  ✅ scanner.js 完成")
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ⚠️ scanner.js 失败: {e}")
                if self.strong:
                    raise EvolveAbort(f"扫描失败: {e}")
        else:
            # Python 原生回退: guard.full_scan()
            print("  ⚠️ scanner.js 缺失，使用 Python 原生扫描...")
            try:
                guard = PreActionGuard(self.p, strict=self.strong)
                snapshot = guard.full_scan()
                s.output = (
                    f"Python全扫描: {snapshot.total_files}文件/"
                    f"{self._fs(snapshot.total_size)} | "
                    f"{snapshot.issues_count}问题"
                )
                s.status = StepStatus.OK
                print(f"  ✅ {s.output}")
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ❌ Python扫描失败: {e}")
                if self.strong:
                    raise EvolveAbort(f"Python扫描失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── Step 3: 备份 ─────────────────────────────────

    def _s3(self) -> None:
        """Step3 — Git 备份当前状态"""
        s = EvolveStep(name="Step3-备份")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("💾 Step3 Git备份")

        if self.dry:
            s.status = StepStatus.SKIP
            s.output = "DRY-RUN 跳过备份"
            print("  ⏭️ DRY-RUN 跳过")
        else:
            try:
                st = self._cmd("git status --porcelain", silent=True)
                if not st.strip():
                    s.status = StepStatus.SKIP
                    s.output = "无变更，跳过备份"
                    print("  ⏭️ 无变更")
                else:
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    self._cmd("git add -A")
                    self._cmd(
                        f'git commit -m "pre-fix: {ts}"', silent=True
                    )
                    self._backup_commit = self._cmd(
                        "git rev-parse HEAD", silent=True
                    )
                    s.status = StepStatus.OK
                    s.output = f"commit: {self._backup_commit[:12]}"
                    print(f"  ✅ {self._backup_commit[:12]}")
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ❌ 备份失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── Step 4: 修复 ─────────────────────────────────

    def _s4(self) -> None:
        """Step4 — 自动修复；JS 不可用时回退到 Python 模式修复"""
        s = EvolveStep(name="Step4-修复")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("🔧 Step4 自动修复")

        if self._tool("auto-fix.js"):
            try:
                r = self._node("auto-fix.js", f'--project "{self.p}" --confirm')
                s.output = r[:500]
                s.status = StepStatus.OK
                print("  ✅ auto-fix.js 完成")
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ⚠️ auto-fix.js 失败: {e}")
        else:
            # Python 原生回退: 扫描 → 模式匹配 → 自动修复
            print("  ⚠️ auto-fix.js 缺失，使用 Python 原生修复...")
            try:
                guard = PreActionGuard(self.p, strict=self.strong)
                snapshot = guard.full_scan()

                fixed_count = 0
                reported_dangers: List[str] = []

                if snapshot.issues_count > 0:
                    for fitem in snapshot.files:
                        if not fitem.issues:
                            continue
                        fp = os.path.join(self.p, fitem.path)
                        if not os.path.isfile(fp):
                            continue
                        try:
                            with open(
                                fp, "r", encoding="utf-8", errors="ignore"
                            ) as fh:
                                original = fh.read()
                        except Exception:
                            continue

                        modified = original
                        file_fixed = 0

                        # 应用可自动修复的模式
                        for pattern, replacement, desc, can_fix in AUTO_FIX_PATTERNS:
                            if pattern.search(modified):
                                new_text = pattern.sub(replacement, modified)
                                if new_text != modified:
                                    modified = new_text
                                    file_fixed += 1
                                    print(f"    🔧 {fitem.path}: {desc}")

                        # 检查危险模式（仅报告）
                        for pattern, desc in DANGER_PATTERNS_REPORT:
                            if pattern.search(modified):
                                reported_dangers.append(f"{fitem.path}: {desc}")

                        # 写入修复结果
                        if modified != original:
                            if self.dry:
                                print(f"    [DRY] 跳过写入 {fitem.path}")
                            else:
                                try:
                                    with open(fp, "w", encoding="utf-8") as fh:
                                        fh.write(modified)
                                    fixed_count += file_fixed
                                except Exception as e:
                                    print(f"    ❌ 写入失败 {fitem.path}: {e}")

                # 构建输出
                parts = [
                    f"Python修复: 扫描{snapshot.total_files}文件/"
                    f"{snapshot.issues_count}问题/{fixed_count}已修复"
                ]
                if reported_dangers:
                    parts.append(
                        f"{len(reported_dangers)}处需人工审查"
                    )
                    for rd in reported_dangers[:5]:
                        print(f"    ⚠️ {rd}")
                s.output = " | ".join(parts)
                s.status = StepStatus.OK
                print(f"  ✅ {s.output}")
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ❌ Python修复失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── Step 5: 审查 ─────────────────────────────────

    def _s5(self) -> None:
        """Step5 — 审计审查；JS 不可用时回退到 guard 双向检查"""
        s = EvolveStep(name="Step5-审查")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("📋 Step5 审计审查")

        if self._tool("audit.js"):
            try:
                r = self._node("audit.js", f'--project "{self.p}" --strict')
                s.output = r[:800]
                s.status = StepStatus.OK
                print("  ✅ audit.js 完成")

                if "FAIL" in r or "CRITICAL" in r:
                    s.status = StepStatus.FAIL
                    s.error = "审计发现 FAIL/CRITICAL"
                    print("  ⚠️ 审计发现问题!")
                    if self.strong:
                        raise EvolveAbort("审计未通过")
            except EvolveAbort:
                raise
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ⚠️ audit.js 失败: {e}")
                if self.strong:
                    raise EvolveAbort(f"审计失败: {e}")
        else:
            # Python 原生回退: guard 全扫描 + 框架完整性检查
            print("  ⚠️ audit.js 缺失，使用 Python 原生审计...")
            try:
                guard = PreActionGuard(self.p, strict=True)
                snapshot = guard.full_scan()
                fw_check = guard._check_fw()

                issues = snapshot.issues_count
                if not fw_check.get("ok"):
                    issues += fw_check.get("missing", 0)

                s.output = (
                    f"Python审计: {snapshot.total_files}文件/"
                    f"{issues}问题 | "
                    f"框架: {fw_check.get('found', 0)}/"
                    f"{fw_check.get('total', 0)}"
                )

                if issues > 0 and self.strong:
                    s.status = StepStatus.FAIL
                    s.error = f"审计发现 {issues} 问题"
                    print(f"  ⚠️ 发现 {issues} 问题!")
                    raise EvolveAbort(f"审计未通过: {issues}问题")
                elif issues > 0:
                    s.status = StepStatus.OK
                    s.output += " (非严格模式，放行)"
                    print(f"  ⚠️ {s.output}")
                else:
                    s.status = StepStatus.OK
                    print(f"  ✅ {s.output}")
            except EvolveAbort:
                raise
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ❌ Python审计失败: {e}")
                if self.strong:
                    raise EvolveAbort(f"Python审计失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── Step 6: 进化 ─────────────────────────────────

    def _s6(self, desc: str) -> None:
        """Step6 — 提交进化记录"""
        s = EvolveStep(name="Step6-进化")
        s.status = StepStatus.RUNNING
        t0 = time.time()
        print("🧬 Step6 进化记录")

        if self.dry:
            s.status = StepStatus.SKIP
            s.output = "DRY-RUN 跳过提交"
            print("  ⏭️ DRY-RUN 跳过")
        else:
            try:
                # 记录到记忆系统
                if self._tool("memory.js"):
                    ed = desc or "6步进化完成"
                    self._node(
                        "memory.js",
                        f'--project "{self.p}" --evolve "{ed}"',
                    )
                    print("  📦 记忆已记录")

                # Git 提交
                st = self._cmd("git status --porcelain", silent=True)
                if st.strip():
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    self._cmd("git add -A")
                    self._cmd(
                        f'git commit -m "evolve: {desc or ts}"',
                        silent=True,
                    )
                    c = self._cmd("git rev-parse HEAD", silent=True)
                    s.output = f"commit: {c[:12]}"
                    print(f"  ✅ {c[:12]}")
                else:
                    s.output = "无新增变更"
                    print("  ✅ 无新增")

                s.status = StepStatus.OK
            except Exception as e:
                s.status = StepStatus.FAIL
                s.error = str(e)
                print(f"  ❌ 进化提交失败: {e}")

        s.duration = time.time() - t0
        self.rpt.steps.append(s)

    # ── 回滚 ─────────────────────────────────────────

    def _rollback(self) -> None:
        """Git revert 回滚到备份点"""
        if self.dry or not self._backup_commit:
            print("  ⏭️ 跳过回滚 (dry-run 或无备份)")
            return

        print("\n⏪ 回滚中...")
        try:
            self._cmd("git revert HEAD --no-edit", silent=True)
            self.rpt.rollback = True
            print("  ✅ 已回滚")
        except Exception as e:
            print(f"  ❌ 回滚失败: {e}")

    # ── 工具方法 ─────────────────────────────────────

    def _fs(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def _cmd(self, cmd: str, silent: bool = False) -> str:
        """执行 shell 命令 (shell=False, 安全)"""
        if self.dry:
            if not silent:
                print(f"  [DRY] {cmd}")
            return ""
        try:
            r = subprocess.run(
                cmd.split(),
                shell=False,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.p,
            )
            return r.stdout.strip() or r.stderr.strip()
        except subprocess.TimeoutExpired:
            return "⏱️超时"
        except Exception as e:
            return f"❌{e}"

    def _node(self, script: str, args: str = "") -> str:
        """执行 Node.js 脚本 (shell=False, 安全)"""
        if self.dry:
            print(f"  [DRY] node {script} {args}")
            return ""
        try:
            cmd = ["node", os.path.join(self.cline, script)]
            # 安全解析额外参数，避免 shell 注入
            if args:
                try:
                    cmd.extend(shlex.split(args))
                except ValueError:
                    cmd.append(args)
            r = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.cline,
            )
            return r.stdout.strip() or r.stderr.strip()
        except subprocess.TimeoutExpired:
            return "⏱️超时"
        except Exception as e:
            return f"❌{e}"

    def _tool(self, script: str) -> bool:
        """检查外部 JS 工具是否存在"""
        return os.path.exists(os.path.join(self.cline, script))

    def _save(self) -> None:
        """保存进化报告到 Markdown 日志"""
        try:
            fn = f"{datetime.now().strftime('%Y-%m-%d')}.md"
            fp = os.path.join(self.log_dir, fn)
            os.makedirs(self.log_dir, exist_ok=True)

            lines = [
                f"# GBT进化 {datetime.now().strftime('%H:%M')}",
                f"- 项目: {self.rpt.project}",
                f"- 成功: {self.rpt.success}",
                f"- 回滚: {self.rpt.rollback}",
                "",
                "## 步骤",
            ]
            icons = {
                "ok": "✅",
                "fail": "❌",
                "skip": "⏭️",
                "pending": "⏳",
                "running": "🔄",
            }
            for st in self.rpt.steps:
                ic = icons.get(st.status.value, "•")
                lines.append(
                    f"- {ic} **{st.name}** ({st.duration:.1f}s)"
                )
                if st.output:
                    lines.append(f"  `{st.output[:200]}`")
                if st.error:
                    lines.append(f"  > ❌ {st.error}")

            with open(fp, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n\n---\n")
            print(f"\n📄 报告: {fp}")
        except Exception as e:
            print(f"⚠️ 保存失败: {e}")

    def _summary(self) -> None:
        """打印进化摘要"""
        r = self.rpt
        print(f"\n{'=' * 50}\n  🧬 {'✅ 成功' if r.success else '❌ 失败'}")
        icons = {"ok": "✅", "fail": "❌", "skip": "⏭️"}
        for st in r.steps:
            print(
                f"  {icons.get(st.status.value, '•')} {st.name} "
                f"({st.duration:.1f}s)"
            )
        if r.rollback:
            print("  ⏪ 已回滚")
        print(f"{'=' * 50}\n")


# ── 便捷函数 ─────────────────────────────────────────────

def run_evolve(
    project: str,
    desc: str = "",
    dry: bool = False,
    strong: bool = False,
) -> EvolveReport:
    """一行式调用进化引擎

    Args:
        project: 项目根目录路径
        desc: 进化描述
        dry: True 时仅分析不写入
        strong: True 时遇到问题立即中止
    """
    return EvolveEngine(project, dry_run=dry, strong=strong).run(desc)


# ── 沙盒验证 ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # 项目根目录 = 当前文件的祖父目录 (gbt/evolve.py → GBTXIAOTUDOUAI/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # gbt/ → GBTXIAOTUDOUAI/

    print(f"🧬 evolve.py 沙盒验证")
    print(f"   项目根: {project_root}")
    print(f"   Python:  {sys.version}")

    # dry_run=True: 仅分析不写入，安全验证全流程
    engine = EvolveEngine(
        project_root,
        dry_run=True,
        strong=False,  # 非严格，即使发现问题也继续
    )
    report = engine.run(desc="沙盒验证: evolve.py 6步闭环测试")

    # 结果检查
    print("\n" + "=" * 60)
    print("📊 沙盒验证结果")
    print(f"   整体成功: {report.success}")
    print(f"   回滚:     {report.rollback}")
    print(f"   摘要:     {report.summary}")

    step_statuses = {s.name: s.status for s in report.steps}
    all_ok = all(
        s.status in (StepStatus.OK, StepStatus.SKIP)
        for s in report.steps
    )

    if all_ok:
        print("   ✅ 全部6步通过 (OK/SKIP)")
        sys.exit(0)
    else:
        print("   ❌ 存在失败步骤:")
        for s in report.steps:
            if s.status == StepStatus.FAIL:
                print(f"      - {s.name}: {s.error}")
        sys.exit(1)
