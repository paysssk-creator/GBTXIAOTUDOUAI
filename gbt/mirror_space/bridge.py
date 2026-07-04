"""GBT Pro — 镜像多维度空间适配层（插件入口）

把仓库 paysssk-creator/jingxiangduoweidukongjian 的 sandbox/* 抽象成
可被桌面主进程以及外部 Agent 调用的统一 skill 入口。

约定：
  - sandbox/ 路径通过 env GBT_MIRROR_SANDBOX_DIR 指定；
    默认就是 gbt/mirror_space/
  - 一切动作都通过 invoke_skill / invoke_pipeline 走子进程 + 镜像副本
    （铁律 1：所有模拟/测试/编程必须在镜像空间执行）
  - 失败总是 Result 形式返回，不抛异常
"""

# 开发者: 自由的风
from __future__ import annotations
import os, sys, json, time, shutil, subprocess, threading, logging, re
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("gbt.mirror.bridge")

SANDBOX_DIR = Path(os.environ.get(
    "GBT_MIRROR_SANDBOX_DIR",
    str(Path(__file__).resolve().parent)
))
PROJECT_DIR = Path(os.environ.get(
    "GBT_PROJECT_DIR",
    str(SANDBOX_DIR.parent.parent)
))
WINDOWS_PATH_RE = re.compile(r"(?i)(?:[A-Z]:\\|\\\\)[^\s\"'\r\n]+")


class Result:
    __slots__ = ("ok", "stage", "code", "logs", "started", "ended", "result")

    def __init__(self, ok: bool, stage: str, code: int = 0,
                 logs: str = "", started: Optional[float] = None,
                 ended: Optional[float] = None, result=None):
        self.ok = ok
        self.stage = stage
        self.code = code
        self.logs = logs
        self.started = started or time.time()
        self.ended = ended
        self.result = result

    def to_dict(self):
        return {
            "ok": self.ok,
            "stage": self.stage,
            "code": self.code,
            "logs": _sanitize_value(self.logs[-4000:] if self.logs else ""),
            "started": self.started,
            "ended": self.ended or time.time(),
            "result": _sanitize_value(self.result),
        }


def _display_dir(path: Path) -> str:
    path = Path(path)
    try:
        if getattr(sys, "frozen", False):
            runtime_root = Path(sys.executable).resolve().parent
            rel = path.resolve().relative_to(runtime_root)
            return "[runtime]/" + str(rel).replace("\\", "/")
        rel = path.resolve().relative_to(PROJECT_DIR.resolve())
        return "[project]/" + str(rel).replace("\\", "/")
    except Exception:
        return path.name or "[path]"


def _scrub_path(raw: str) -> str:
    try:
        p = Path(raw)
    except Exception:
        return "[path]"
    parts = [x.lower() for x in p.parts]
    if "screenshots" in parts:
        return "screenshots/" + p.name
    if "reports" in parts:
        return "reports/" + p.name
    if p.suffix:
        return p.name
    return p.name or "[path]"


def _sanitize_text(value: str) -> str:
    if not value:
        return value
    value = value.replace(str(SANDBOX_DIR), _display_dir(SANDBOX_DIR))
    value = value.replace(str(PROJECT_DIR), _display_dir(PROJECT_DIR))
    return WINDOWS_PATH_RE.sub(lambda m: _scrub_path(m.group(0)), value)


def _sanitize_value(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in {"project_dir", "sandbox_dir"}:
                out[k] = _display_dir(PROJECT_DIR if k == "project_dir" else SANDBOX_DIR)
            elif k == "file":
                out[k] = _scrub_path(str(v))
            else:
                out[k] = _sanitize_value(v)
        return out
    if isinstance(value, list):
        return [_sanitize_value(x) for x in value]
    if isinstance(value, tuple):
        return [_sanitize_value(x) for x in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _python_candidates():
    override = os.environ.get("GBT_MIRROR_PYTHON", "").strip()
    if override:
        yield override
    if not getattr(sys, "frozen", False):
        yield sys.executable
    else:
        exe_dir = Path(sys.executable).resolve().parent
        yield str(exe_dir / "python.exe")
        yield str(exe_dir / "_internal" / "python.exe")
    for name in ("python", "py"):
        yield shutil.which(name) or ""


def _py():
    for cand in _python_candidates():
        if not cand:
            continue
        cpath = Path(cand)
        if cpath.name.lower() in {"python", "py"}:
            return cand
        if cpath.exists():
            return str(cpath)
    return ""


def _worker_unavailable(stage: str) -> Result:
    msg = (
        "mirror worker unavailable: desktop package has no usable python worker; "
        "invoke is blocked instead of hanging"
    )
    return Result(False, stage, -3, msg, result={"reason": msg})


def _build_args(opts) -> list[str]:
    extras = []
    for k, v in opts.items():
        if isinstance(v, bool):
            if v:
                extras.append(f"--{k}")
        elif v not in (None, ""):
            extras.extend(["--" + k, str(v)])
    return extras


def _run(cmd, cwd=None, t=1800, stage: str = "mirror") -> Result:
    started = time.time()
    env = os.environ.copy()
    sp = env.get("PYTHONPATH") or ""
    parts = [str(SANDBOX_DIR)]
    if sp:
        parts.append(sp)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    try:
        p = subprocess.run(
            cmd, cwd=cwd or str(SANDBOX_DIR), shell=False,
            capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=t,
            env=env,
        )
        return Result(
            ok=(p.returncode == 0),
            stage=stage,
            code=p.returncode,
            logs=(p.stdout or "") + (p.stderr or ""),
            started=started,
            ended=time.time(),
        )
    except subprocess.TimeoutExpired:
        return Result(False, stage, -1, "timeout", started, time.time())
    except Exception as e:
        return Result(False, stage, -2, str(e), started, time.time())


# ── 0) 状态：列出已"装上"的能力与目录 ──
def status() -> dict:
    files = sorted([p.name for p in SANDBOX_DIR.glob("*.py")])
    return _sanitize_value({
        "ok": True,
        "sandbox_dir": str(SANDBOX_DIR),
        "project_dir": str(PROJECT_DIR),
        "modules": files,
        "skills": [
            "full", "evolve", "canary", "rollback", "rollback-drill",
            "validate", "monitor", "list", "pipeline", "build-registry"
        ],
        "version": time.strftime("%Y%m%d.%H%M"),
    })


def _orchestrator_script() -> Path:
    return SANDBOX_DIR / "sandbox-orchestrator.py"


def _invoke_args(skill: str, project: str, opts: dict) -> list[str]:
    cmd = [_py(), str(_orchestrator_script()), "--project", project]
    stage_flag = {
        "full": ["--full", "--deploy"],
        "canary": ["--canary"],
        "rollback": ["--rollback"],
        "monitor": ["--monitor"],
        "validate": ["--validate"],
        "rollback-drill": ["--rollback-drill"],
    }.get(skill)
    if not stage_flag:
        raise ValueError(f"unknown skill: {skill}")
    cmd.extend(stage_flag)
    cmd.extend(_build_args(opts))
    return cmd


# ── 1) 通用：invoke_skill → 调 mirror_skill.py ──
def invoke_skill(skill: str = "full", project: str = None, **opts) -> Result:
    """调用 mirror_skill.py

    skill ∈ full / evolve / canary / rollback / monitor / validate / rollback-drill
    opts 传给 sandbox-orchestrator.py，例如 target / canary / module
    """
    project = str(Path(project or PROJECT_DIR).resolve())
    py_cmd = _py()
    if not py_cmd:
        return _worker_unavailable(skill)
    cmd = _invoke_args(skill, project, opts)
    return _run(cmd, cwd=str(SANDBOX_DIR), t=2400, stage=skill)


# ── 2) 高级：直接调 sandbox-orchestrator.py 子动作 ──
def invoke_orchestrator(action: str, project: str = None, **opts) -> Result:
    project = str(Path(project or PROJECT_DIR).resolve())
    py_cmd = _py()
    if not py_cmd:
        return _worker_unavailable(action)
    cmd = [py_cmd, str(_orchestrator_script()), "--project", project, "--" + action]
    cmd.extend(_build_args(opts))
    return _run(cmd, cwd=str(SANDBOX_DIR), t=1800, stage=action)


# ── 3) 镜像主动技能：自动发现模块契约 ──
def build_module_registry(project: str = None) -> Result:
    project = str(Path(project or PROJECT_DIR).resolve())
    py_cmd = _py()
    if not py_cmd:
        return _worker_unavailable("build-registry")
    cmd = [py_cmd, str(SANDBOX_DIR / "module_registry.py"), "--project", project]
    r = _run(cmd, cwd=str(SANDBOX_DIR), t=120, stage="build-registry")
    reg_path = Path.home() / ".gbt" / "sandbox" / "module-registry.json"
    if reg_path.exists():
        try:
            r.result = json.loads(reg_path.read_text(encoding="utf-8"))
        except Exception:
            r.result = None
    return r


# ── 4) 自演化：evolve_project 限轮 ──
def evolve(project: str = None, dry_run: bool = True, rounds: int = 1) -> Result:
    project = str(Path(project or PROJECT_DIR).resolve())
    py_cmd = _py()
    if not py_cmd:
        return _worker_unavailable("evolve")
    extras = ["--rounds", str(rounds)] if rounds else []
    if dry_run:
        extras.append("--dry-run")
    cmd = [py_cmd, str(SANDBOX_DIR / "scheduler.py"), "--project", project, "--evolve", *extras]
    return _run(cmd, cwd=str(SANDBOX_DIR), t=2400, stage="evolve")


# ── 5) Pipeline：sandbox full + 列表里 pipeline 标注的模块 ──
def pipeline(project: str = None, dry_run: bool = True) -> Result:
    project = str(Path(project or PROJECT_DIR).resolve())
    py_cmd = _py()
    if not py_cmd:
        return _worker_unavailable("pipeline")
    cmd = [py_cmd, str(SANDBOX_DIR / "scheduler.py"), "--project", project, "--pipeline"]
    if dry_run:
        cmd.append("--dry-run")
    return _run(cmd, cwd=str(SANDBOX_DIR), t=1800, stage="pipeline")


# ── 6) 生成 / 查看最新报告 ──
def latest_report() -> dict:
    reports = Path.home() / ".gbt" / "sandbox" / "reports"
    if not reports.exists():
        return {"ok": False, "reason": "no reports directory"}
    files = sorted(reports.glob("*-review.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {"ok": False, "reason": "no review reports yet"}
    p = files[0]
    try:
        return _sanitize_value({"ok": True, "file": str(p), "report": json.loads(p.read_text(encoding="utf-8"))})
    except Exception as e:
        return {"ok": False, "reason": str(e)}


# ── 7) 模块列表（从 ~/.gbt/sandbox/modules/*.json 读取） ──
def list_modules() -> dict:
    mods_dir = Path.home() / ".gbt" / "sandbox" / "modules"
    if not mods_dir.exists():
        return {"ok": True, "modules": [], "note": "未注册模块；运行一次 build_module_registry 即生成"}
    out = []
    for p in sorted(mods_dir.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return _sanitize_value({"ok": True, "modules": out})


# ── 8) 兼容简易：直接 exec sandbox-orchestrator 入口（只 dry-run） ──
def safe_dry_run(project: str = None) -> Result:
    project = str(Path(project or PROJECT_DIR).resolve())
    return invoke_orchestrator("full", project=project, dry_run=True, deploy=False)


def active_skill_doc() -> str:
    """把当前 sandbox 的能力告诉任何 Agent — 这就是 README 里"主动技能"含义"""
    return (
        "── Mirror Multi-Dimensional Space · Active Skill ──\n"
        "  1) 所有模拟/测试/编程必须在镜像空间执行（sandbox 启动独立副本）\n"
        "  2) 生产部署只能是原子模块替换（一次性路由切换，不可变制品）\n"
        "  3) 生产面板只放生产级代码（无占位 / 无假数据 / 无空壳 / 无硬编码密钥）\n"
        "  4) 未通过完整 sandbox，禁止部署\n"
        "可用主动技能：\n"
        "  full / evolve / canary / rollback / rollback-drill / validate / monitor\n"
        "  build-registry / pipeline / list / status\n"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="status")
    ap.add_argument("--project")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    fn = {
        "status": lambda: status(),
        "full": lambda: invoke_skill("full", args.project, dry_run=args.dry_run),
        "evolve": lambda: invoke_skill("evolve", args.project, dry_run=args.dry_run),
        "canary": lambda: invoke_skill("canary", args.project, dry_run=args.dry_run),
        "rollback": lambda: invoke_skill("rollback", args.project, dry_run=args.dry_run),
        "monitor": lambda: invoke_skill("monitor", args.project, dry_run=args.dry_run),
        "validate": lambda: invoke_skill("validate", args.project, dry_run=args.dry_run),
        "rollback-drill": lambda: invoke_skill("rollback-drill", args.project, dry_run=args.dry_run),
        "build-registry": lambda: build_module_registry(args.project),
        "pipeline": lambda: pipeline(args.project, dry_run=args.dry_run),
        "active-skill-doc": lambda: {"doc": active_skill_doc()},
        "report": lambda: latest_report(),
    }.get(args.cmd, lambda: {"ok": False, "reason": "unknown cmd: " + args.cmd})
    r = fn()
    if isinstance(r, Result):
        r = r.to_dict()
    print(json.dumps(r, ensure_ascii=False, indent=2))
