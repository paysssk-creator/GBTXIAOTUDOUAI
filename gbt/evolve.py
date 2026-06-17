"""
evolve.py — 6步自进化闭环引擎
自查→扫描→备份→修复→审查→进化
"""

import os, subprocess, json, time
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum
from .guard import PreActionGuard  # 行动前守卫

class StepStatus(Enum):
    PENDING="pending"; RUNNING="running"; OK="ok"; FAIL="fail"; SKIP="skip"

@dataclass
class EvolveStep:
    name: str; status: StepStatus = StepStatus.PENDING
    output: str=""; error: str=""; duration: float=0.0

@dataclass
class EvolveReport:
    project: str; started: str; finished: str=""
    steps: List[EvolveStep] = field(default_factory=list)
    success: bool=False; rollback: bool=False; summary: str=""

class EvolveAbort(Exception): pass


class EvolveEngine:
    """6步自进化闭环引擎"""

    def __init__(self, project_root: str, dry_run: bool = False,
                 strong: bool = False, log_dir: Optional[str] = None):
        self.p = os.path.abspath(project_root)
        self.dry = dry_run; self.strong = strong
        self.log_dir = log_dir or os.path.join(self.p, ".gbt", "evolve-logs")
        self.cline = os.path.join(os.path.expanduser("~"), ".cline")
        self.rpt: Optional[EvolveReport] = None
        self._backup_commit = ""

    def run(self, desc: str = "") -> EvolveReport:
        self.rpt = EvolveReport(project=self.p, started=datetime.now().isoformat())
        os.makedirs(self.log_dir, exist_ok=True)
        print(f"\n{'='*50}\n  🧬 6步闭环 — {self.p}\n  {'🏃DRY' if self.dry else '💪实跑'}\n{'='*50}\n")
        try:
            self._s1(); self._s2(); self._s3()
            self._s4(); self._s5(); self._s6(desc)
            self.rpt.success = True
        except EvolveAbort as e:
            self.rpt.summary = f"中止:{e}"; self._rollback()
        except Exception as e:
            self.rpt.summary = f"异常:{e}"; self._rollback()
        self.rpt.finished = datetime.now().isoformat()
        self._save(); self._summary()
        return self.rpt

    # ── Step 1: 自查 ──
    def _s1(self):
        s = EvolveStep(name="Step1-自查"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("🔍 Step1 强制全项目扫描(零跳过)")
        try:
            guard = PreActionGuard(self.p, strict=self.strong)
            snapshot = guard.full_scan()
            s.output = (f"全扫描完成: {snapshot.total_files}文件/"
                       f"{self._fs(snapshot.total_size)} | "
                       f"{snapshot.issues_count}问题")
            s.status = StepStatus.OK
            print(f"  ✅ {s.output}")
            if guard.is_blocked and self.strong:
                raise EvolveAbort(f"安全隐患:{snapshot.issues_count}个")
        except EvolveAbort: raise
        except Exception as e:
            s.status = StepStatus.FAIL; s.error = str(e)
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    def _fs(self, size: int) -> str:
        for u in ["B","KB","MB","GB"]:
            if size < 1024: return f"{size:.1f}{u}"
            size /= 1024
        return f"{size:.1f}TB"

    # ── Step 2: 发现问题 ──
    def _s2(self):
        s = EvolveStep(name="Step2-扫描"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("🔎 Step2 scanner")
        if not self._tool("scanner.js"):
            s.status = StepStatus.SKIP; print("  ⏭️ 跳过")
        else:
            try:
                r = self._node("scanner.js", f'--project "{self.p}"')
                s.output = r[:800]; s.status = StepStatus.OK
                print("  ✅ 完成")
            except Exception as e:
                s.status = StepStatus.FAIL; s.error = str(e)
                if self.strong: raise EvolveAbort(f"扫描失败:{e}")
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    # ── Step 3: 备份 ──
    def _s3(self):
        s = EvolveStep(name="Step3-备份"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("💾 Step3 git备份")
        if self.dry:
            s.status = StepStatus.SKIP; print("  ⏭️ DRY跳过")
        else:
            try:
                st = self._cmd("git status --porcelain", silent=True)
                if not st.strip():
                    s.status = StepStatus.SKIP; s.output = "无变更"
                    print("  ⏭️ 无变更")
                else:
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    self._cmd("git add -A")
                    self._cmd(f'git commit -m "pre-fix: {ts}"', silent=True)
                    self._backup_commit = self._cmd("git rev-parse HEAD", silent=True)
                    s.status = StepStatus.OK
                    s.output = f"commit:{self._backup_commit[:12]}"
                    print(f"  ✅ {self._backup_commit[:12]}")
            except Exception as e:
                s.status = StepStatus.FAIL; s.error = str(e)
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    # ── Step 4: 修复 ──
    def _s4(self):
        s = EvolveStep(name="Step4-修复"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("🔧 Step4 修复")
        if self._tool("auto-fix.js"):
            try:
                r = self._node("auto-fix.js", f'--project "{self.p}" --confirm')
                s.output = r[:500]; s.status = StepStatus.OK
                print("  ✅ auto-fix完成")
            except Exception as e:
                s.status = StepStatus.FAIL; s.error = str(e)
        else:
            s.status = StepStatus.SKIP; s.output = "Cline editor执行"
            print("  ⏭️ editor执行")
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    # ── Step 5: 审查 ──
    def _s5(self):
        s = EvolveStep(name="Step5-审查"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("📋 Step5 audit")
        if not self._tool("audit.js"):
            s.status = StepStatus.SKIP; print("  ⏭️ 跳过")
        else:
            try:
                r = self._node("audit.js", f'--project "{self.p}" --strict')
                s.output = r[:800]; s.status = StepStatus.OK
                print("  ✅ 审计完成")
                if "FAIL" in r or "CRITICAL" in r:
                    s.status = StepStatus.FAIL; s.error = "审计FAIL"
                    print("  ⚠️ 发现问题!")
                    if self.strong: raise EvolveAbort("审计未通过")
            except EvolveAbort: raise
            except Exception as e:
                s.status = StepStatus.FAIL; s.error = str(e)
                if self.strong: raise EvolveAbort(f"审计失败:{e}")
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    # ── Step 6: 进化 ──
    def _s6(self, desc: str):
        s = EvolveStep(name="Step6-进化"); s.status = StepStatus.RUNNING
        t0 = time.time(); print("🧬 Step6 进化")
        if self.dry:
            s.status = StepStatus.SKIP; print("  ⏭️ DRY跳过")
        else:
            try:
                if self._tool("memory.js"):
                    self._node("memory.js",
                        f'--project "{self.p}" --evolve "{desc or \"6步进化完成\"}"')
                    print("  📦 记忆记录")
                st = self._cmd("git status --porcelain", silent=True)
                if st.strip():
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    self._cmd("git add -A")
                    self._cmd(f'git commit -m "evolve: {desc or ts}"', silent=True)
                    c = self._cmd("git rev-parse HEAD", silent=True)
                    s.output = f"commit:{c[:12]}"
                    print(f"  ✅ {c[:12]}")
                else:
                    s.output = "无新增"; print("  ✅ 无新增")
                s.status = StepStatus.OK
            except Exception as e:
                s.status = StepStatus.FAIL; s.error = str(e)
        s.duration = time.time()-t0; self.rpt.steps.append(s)

    # ── 回滚 ──
    def _rollback(self):
        if self.dry or not self._backup_commit:
            print("  ⏭️ 跳过回滚"); return
        print("\n⏪ 回滚中...")
        try:
            self._cmd("git revert HEAD --no-edit", silent=True)
            self.rpt.rollback = True; print("  ✅ 已回滚")
        except Exception as e:
            print(f"  ❌ 回滚失败:{e}")

    # ── 工具方法 ──
    def _cmd(self, cmd: str, silent: bool = False) -> str:
        if self.dry:
            if not silent: print(f"  [DRY] {cmd}")
            return ""
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                text=True, timeout=60, cwd=self.p)
            return r.stdout.strip() or r.stderr.strip()
        except: return ""

    def _node(self, script: str, args: str = "") -> str:
        if self.dry: print(f"  [DRY] node {script} {args}"); return ""
        try:
            cmd = f'node "{os.path.join(self.cline, script)}" {args}'
            r = subprocess.run(cmd, shell=True, capture_output=True,
                text=True, timeout=120, cwd=self.cline)
            return r.stdout.strip() or r.stderr.strip()
        except subprocess.TimeoutExpired: return "⏱️超时"
        except Exception as e: return f"❌{e}"

    def _tool(self, script: str) -> bool:
        return os.path.exists(os.path.join(self.cline, script))

    def _save(self):
        try:
            fn = f"{datetime.now().strftime('%Y-%m-%d')}.md"
            fp = os.path.join(self.log_dir, fn)
            os.makedirs(self.log_dir, exist_ok=True)
            lines = [f"# GBT进化 {datetime.now().strftime('%H:%M')}",
                f"- 项目:{self.rpt.project}", f"- 成功:{self.rpt.success}",
                f"- 回滚:{self.rpt.rollback}", "", "## 步骤"]
            icons = {"ok":"✅","fail":"❌","skip":"⏭️","pending":"⏳","running":"🔄"}
            for s in self.rpt.steps:
                ic = icons.get(s.status.value, "•")
                lines.append(f"- {ic} **{s.name}** ({s.duration:.1f}s)")
                if s.output: lines.append(f"  `{s.output[:200]}`")
                if s.error: lines.append(f"  > ❌ {s.error}")
            with open(fp, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n\n---\n")
            print(f"\n📄 报告: {fp}")
        except Exception as e:
            print(f"⚠️ 保存失败:{e}")

    def _summary(self):
        r = self.rpt
        print(f"\n{'='*50}\n  🧬 {'成功' if r.success else '失败'}")
        icons = {"ok":"✅","fail":"❌","skip":"⏭️"}
        for s in r.steps:
            print(f"  {icons.get(s.status.value,'•')} {s.name} ({s.duration:.1f}s)")
        if r.rollback: print("  ⏪ 已回滚")
        print(f"{'='*50}\n")


def run_evolve(project: str, desc: str = "",
               dry: bool = False, strong: bool = False) -> EvolveReport:
    return EvolveEngine(project, dry_run=dry, strong=strong).run(desc)
