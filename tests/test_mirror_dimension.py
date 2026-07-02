# -*- coding: utf-8 -*-
"""镜像多维度空间 — 核心引擎测试"""
import os, sys, tempfile, pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mirror_dimension.scanner import ProjectScanner, DANGER_PATTERNS, FAKE_PATTERNS
from mirror_dimension.auditor import ProjectAuditor
from mirror_dimension.fixer import SandboxFixer
from mirror_dimension.dimensions import DimensionTester
from mirror_dimension.pipeline import MirrorPipeline


class TestScanner:
    """全量扫描引擎测试"""

    def test_detects_hardcoded_key(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"', encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["dangers"] >= 1
        assert any("HARDCODE_API_KEY" in d["type"] for d in r["danger_items"])

    def test_detects_eval(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("eval('1+1')", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["dangers"] >= 1
        assert any("DANGER_EVAL" in d["type"] for d in r["danger_items"])

    def test_detects_todo(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("# TODO: implement this", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["fakes"] >= 1
        assert any("TODO_PLACEHOLDER" in d["type"] for d in r["fake_items"])

    def test_detects_bare_except(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("try:\n    pass\nexcept:\n    pass", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["dangers"] >= 1
        assert any("BARE_EXCEPT" in d["type"] for d in r["danger_items"])

    def test_detects_syntax_error(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def broken(\n", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert not r["clean"]

    def test_clean_file_passes(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def hello():\n    return 'world'", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["clean"]

    def test_skips_git_dir(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        (git / "config.py").write_text("API_KEY = 'leak'", encoding="utf-8")
        s = ProjectScanner(str(tmp_path))
        r = s.scan()
        assert r["clean"]  # .git 被跳过

    def test_danger_patterns_not_empty(self):
        assert len(DANGER_PATTERNS) >= 10
        assert len(FAKE_PATTERNS) >= 10

    def test_scan_project_shortcut(self, tmp_path):
        from mirror_dimension.scanner import scan_project
        (tmp_path / "ok.py").write_text("x = 1", encoding="utf-8")
        r = scan_project(str(tmp_path))
        assert r["clean"]


class TestAuditor:
    """深度审计引擎测试"""

    def test_detects_env_file(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=abc", encoding="utf-8")
        a = ProjectAuditor(str(tmp_path))
        r = a.audit()
        assert len(r["sensitive_files"]) >= 1

    def test_no_gitignore_is_gap(self, tmp_path):
        a = ProjectAuditor(str(tmp_path))
        r = a.audit()
        assert "NO_GITIGNORE_FILE" in r["gitignore_gaps"]

    def test_complete_gitignore_passes(self, tmp_path):
        (tmp_path / ".gitignore").write_text(
            ".env\n*.db\n*.sqlite\n*.pem\n*.key\n__pycache__\n*.pyc\ndata/\n", encoding="utf-8")
        a = ProjectAuditor(str(tmp_path))
        r = a.audit()
        assert r["clean"]

    def test_missing_gitignore_rules(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        a = ProjectAuditor(str(tmp_path))
        r = a.audit()
        assert not r["clean"]


class TestFixer:
    """沙盒修复引擎测试"""

    def test_fixes_bare_except(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("try:\n    pass\nexcept:\n    pass", encoding="utf-8")
        fixer = SandboxFixer(str(tmp_path), dry_run=True)
        r = fixer.run()
        assert r["fixes_applied"] >= 1

    def test_fixes_shell_true(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("subprocess.run(['ls'], shell=True)", encoding="utf-8")
        fixer = SandboxFixer(str(tmp_path), dry_run=True)
        r = fixer.run()
        assert r["fixes_applied"] >= 1

    def test_dry_run_does_not_modify(self, tmp_path):
        f = tmp_path / "test.py"
        original = "try:\n    pass\nexcept:\n    pass"
        f.write_text(original, encoding="utf-8")
        fixer = SandboxFixer(str(tmp_path), dry_run=True)
        fixer.run()
        assert f.read_text(encoding="utf-8") == original

    def test_real_run_modifies(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("try:\n    pass\nexcept:\n    pass", encoding="utf-8")
        fixer = SandboxFixer(str(tmp_path), dry_run=False)
        fixer.run()
        content = f.read_text(encoding="utf-8")
        assert "except:" not in content


class TestDimensions:
    """四维度测试引擎测试"""

    def test_dimensions_has_four(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        d = DimensionTester(str(tmp_path))
        r = d.test()
        assert "user" in r
        assert "developer" in r
        assert "ops" in r
        assert "security" in r
        assert r["user"]["score"] == 20  # has entry + readme

    def test_dimensions_scores_in_range(self, tmp_path):
        (tmp_path / "main.py").write_text('"""doc"""\nx=1', encoding="utf-8")
        d = DimensionTester(str(tmp_path))
        r = d.test()
        for dim in ["user", "developer", "ops", "security"]:
            assert 0 <= r[dim]["score"] <= 20

    def test_no_eval_scores_high(self, tmp_path):
        (tmp_path / "main.py").write_text("print('safe')", encoding="utf-8")
        d = DimensionTester(str(tmp_path))
        r = d.test()
        assert r["security"]["score"] == 20

    def test_has_eval_scores_low(self, tmp_path):
        (tmp_path / "main.py").write_text("eval('1+1')", encoding="utf-8")
        d = DimensionTester(str(tmp_path))
        r = d.test()
        assert r["security"]["score"] <= 10


class TestPipeline:
    """完整管道测试"""

    def test_full_pipeline_runs(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Project", encoding="utf-8")
        (tmp_path / ".gitignore").write_text(
            ".env\n*.db\n*.sqlite\n*.pem\n*.key\n__pycache__\n*.pyc\ndata/\n", encoding="utf-8")
        p = MirrorPipeline(str(tmp_path), dry_run=True)
        r = p.run()
        assert "stages" in r
        assert "scan" in r["stages"]
        assert "audit" in r["stages"]
        assert "fix" in r["stages"]
        assert "dimensions" in r["stages"]
        assert r["verdict"] in ("PASS", "WARN", "FAIL")
