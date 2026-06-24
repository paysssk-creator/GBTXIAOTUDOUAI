"""
build-gbt-sidecar.py — Build the GBT Python backend as a Tauri sidecar binary.
Usage:
    python scripts/tauri/build-gbt-sidecar.py [--target x86_64-pc-windows-msvc]

The output is placed in dist/ and then staged by stage-gbt-sidecar.sh.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = ROOT / "gbt-sidecar.spec"


def find_pyinstaller() -> str:
    candidates = [
        ROOT / ".venv" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv_cradle_py310" / "Scripts" / "pyinstaller.exe",
        ROOT / "venv_cradle" / "Scripts" / "pyinstaller.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "pyinstaller"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GBT Tauri sidecar")
    parser.add_argument("--target", default=None, help="Rust target triple (used for naming only)")
    args = parser.parse_args()

    if not SPEC.exists():
        print(f"Spec not found: {SPEC}")
        return 1

    pyinstaller = find_pyinstaller()
    cmd = [pyinstaller, "--noconfirm", "--clean", str(SPEC)]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    print("Building sidecar...")
    print(" ".join(cmd))
    result = subprocess.call(cmd, cwd=str(ROOT), env=env)
    if result != 0:
        print("PyInstaller build failed")
        return result

    # Print expected output path so stage script can find it
    ext = ".exe" if sys.platform == "win32" else ""
    out = ROOT / "dist" / f"gbt-sidecar{ext}"
    if out.exists():
        print(f"Sidecar built: {out}")
    else:
        print(f"Expected output not found: {out}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
