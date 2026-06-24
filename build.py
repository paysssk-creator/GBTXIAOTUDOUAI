# -*- coding: utf-8 -*-
"""
GBT AI Workstation — Professional Build Script v1.0
Builds the Windows EXE via PyInstaller and optionally the Docker image.
Usage:
    python build.py              # build EXE only
    python build.py --docker     # build EXE + Docker image
    python build.py --clean-only # just kill old processes and clean artifacts
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "gbt.spec"
ENTRY_PY = ROOT / "entry.py"


def log(msg: str) -> None:
    print(f"[BUILD] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> int:
    """Run a command and stream output."""
    log(" ".join(cmd))
    return subprocess.call(cmd, **kwargs)


def kill_old_processes() -> None:
    """Terminate stale GBT application processes before repackaging to avoid file locks."""
    log("Cleaning old GBT processes...")
    names = ["GBT.exe", "GBTWorkstation.exe"]
    for name in names:
        try:
            # taskkill /F /IM ensures force-kill by image name
            subprocess.run(
                ["taskkill", "/F", "/IM", name, "/T"],
                capture_output=True,
                check=False,
            )
        except Exception as e:
            log(f"taskkill {name} skipped: {e}")
    # Give the OS a moment to release file handles
    time.sleep(1)


def clean_artifacts() -> None:
    """Remove previous PyInstaller outputs."""
    log("Removing old build artifacts...")
    for path in [BUILD_DIR, DIST_DIR / "GBTWorkstation"]:
        if path.exists():
            try:
                shutil.rmtree(path)
                log(f"Removed {path}")
            except Exception as e:
                log(f"Failed to remove {path}: {e}")


def find_pyinstaller() -> str:
    """Prefer venv PyInstaller, fall back to PATH."""
    candidates = [
        ROOT / ".venv" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv_cradle_py310" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv_cradle" / "Scripts" / "pyinstaller.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # Fallback to whatever is on PATH
    return "pyinstaller"


def build_exe() -> int:
    """Run PyInstaller with the project spec."""
    if not SPEC_FILE.exists():
        log(f"Spec file not found: {SPEC_FILE}")
        return 1

    pyinstaller = find_pyinstaller()
    cmd = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return run(cmd, cwd=str(ROOT), env=env)


def build_docker() -> int:
    """Build the headless Docker image."""
    log("Building Docker image...")
    return run(
        ["docker", "build", "-t", "gbt-ai-workstation", "."],
        cwd=str(ROOT),
    )


def sanity_check_dist() -> int:
    """Verify the produced EXE exists."""
    exe = DIST_DIR / "GBT.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        log(f"Output OK: {exe} ({size_mb:.1f} MB)")
        return 0
    log(f"Output missing: {exe}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="GBT Workstation build script")
    parser.add_argument("--docker", action="store_true", help="Also build Docker image")
    parser.add_argument("--clean-only", action="store_true", help="Only clean processes and artifacts")
    args = parser.parse_args()

    if args.clean_only:
        kill_old_processes()
        clean_artifacts()
        return 0

    kill_old_processes()
    clean_artifacts()

    rc = build_exe()
    if rc != 0:
        log("EXE build failed")
        return rc

    rc = sanity_check_dist()
    if rc != 0:
        return rc

    if args.docker:
        rc = build_docker()
        if rc != 0:
            log("Docker build failed")
            return rc

    log("Build completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
