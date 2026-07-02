# -*- coding: utf-8 -*-
"""完整管道编排器 — scan → audit → fix → dimensions"""
import time
from datetime import datetime
from typing import Optional

from .scanner import ProjectScanner
from .auditor import ProjectAuditor
from .fixer import SandboxFixer
from .dimensions import DimensionTester


class MirrorPipeline:
    """镜像多维度空间完整管道编排器"""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.root = project_root
        self.dry_run = dry_run
        self.report = {
            "project": project_root,
            "timestamp": datetime.now().isoformat(),
            "stages": {},
            "exit_code": 0,
        }

    def run(self) -> dict:
        t0 = time.time()

        # Stage 1: Scan
        scan = ProjectScanner(self.root).scan()
        self.report["stages"]["scan"] = scan
        if not scan["clean"]:
            self.report["exit_code"] = 1

        # Stage 2: Audit
        audit = ProjectAuditor(self.root).audit()
        self.report["stages"]["audit"] = audit
        if not audit["clean"]:
            self.report["exit_code"] = max(self.report["exit_code"], 1)

        # Stage 3: Fix
        fix = SandboxFixer(self.root, dry_run=self.dry_run).run()
        self.report["stages"]["fix"] = fix
        if not fix["clean"]:
            self.report["exit_code"] = max(self.report["exit_code"], 1)

        # Stage 4: Dimensions
        dims = DimensionTester(self.root).test()
        self.report["stages"]["dimensions"] = dims

        # Summary
        total_duration = sum(
            s.get("duration_s", 0)
            for s in self.report["stages"].values()
            if isinstance(s, dict)
        )
        self.report["total_duration_s"] = round(total_duration, 2)
        stages_ok = sum(
            1 for s in self.report["stages"].values()
            if isinstance(s, dict) and s.get("clean", True)
        )
        self.report["stages_passed"] = f"{stages_ok}/4"

        avg_score = dims.get("average_score", 0)
        if self.report["exit_code"] == 0:
            self.report["verdict"] = "PASS"
        elif avg_score >= 60:
            self.report["verdict"] = "WARN"
        else:
            self.report["verdict"] = "FAIL"

        return self.report


def run_pipeline(root: str, dry_run: bool = False) -> dict:
    """便捷管道运行"""
    return MirrorPipeline(root, dry_run=dry_run).run()
