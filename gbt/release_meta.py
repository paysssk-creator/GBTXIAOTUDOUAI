"""GBT Pro release metadata.

Provides a single source of truth for desktop/runtime version information so
launchers, APIs, and packaging scripts stop drifting apart.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "GBT Pro"
APP_VERSION = "v1.1.18"
RELEASE_TAG = "v1.1.18-desktop-runtime"
RUNTIME_FLAVOR = "dir_parallel"
RUNTIME_DIRNAME = "GBT_Pro_v1.1.18_dir_parallel"
RUNTIME_EXE = "GBT_Pro_v1.1.18_dir_parallel.exe"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "release"
CANONICAL_RUNTIME_DIR = PROJECT_ROOT / "dist_rebuild_parallel" / RUNTIME_DIRNAME
CANONICAL_RUNTIME_EXE = CANONICAL_RUNTIME_DIR / RUNTIME_EXE
CURRENT_RUNTIME_INI = RELEASE_ROOT / "current_runtime.ini"


def _read_current_runtime_ini() -> dict[str, str]:
    values: dict[str, str] = {}
    if not CURRENT_RUNTIME_INI.exists():
        return values
    for raw_line in CURRENT_RUNTIME_INI.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _prefer_env(env_name: str, fallback: str, *, invalid: set[str] | None = None) -> str:
    value = (os.environ.get(env_name) or "").strip()
    if value and value not in (invalid or set()):
        return value
    return fallback


def _resolve_path(env_name: str, fallback: Path) -> str:
    raw = (os.environ.get(env_name) or "").strip()
    candidate = Path(raw) if raw else fallback
    if not candidate.is_absolute():
        base_dir = Path.cwd() if getattr(sys, "frozen", False) else PROJECT_ROOT
        candidate = base_dir / candidate
    return str(candidate.resolve())


def get_role() -> str:
    default_role = "desktop" if getattr(sys, "frozen", False) else "dev"
    return _prefer_env("GBT_ROLE", default_role, invalid={"", "dev"} if getattr(sys, "frozen", False) else {""})


def get_version() -> str:
    ini_values = _read_current_runtime_ini()
    return _prefer_env("BUILD_HASH", ini_values.get("APP_VERSION", APP_VERSION), invalid={"", "dev", "unknown"})


def get_release_tag() -> str:
    ini_values = _read_current_runtime_ini()
    return _prefer_env("GBT_RELEASE_TAG", ini_values.get("RELEASE_TAG", RELEASE_TAG), invalid={"", "dev", "unknown"})


def get_data_dir() -> str:
    default_dir = Path.cwd() if getattr(sys, "frozen", False) else (PROJECT_ROOT / "data")
    return _resolve_path("GBT_DATA_DIR", default_dir)


def get_log_dir() -> str:
    default_dir = Path.cwd() / "logs" if getattr(sys, "frozen", False) else (PROJECT_ROOT / "logs")
    return _resolve_path("GBT_LOG_DIR", default_dir)


def runtime_identity() -> dict[str, str]:
    ini_values = _read_current_runtime_ini()
    runtime_dir = PROJECT_ROOT / ini_values.get("RUNTIME_DIR", str(CANONICAL_RUNTIME_DIR.relative_to(PROJECT_ROOT)))
    runtime_exe = PROJECT_ROOT / ini_values.get("RUNTIME_EXE", str(CANONICAL_RUNTIME_EXE.relative_to(PROJECT_ROOT)))
    return {
        "app_name": APP_NAME,
        "version": get_version(),
        "release_tag": get_release_tag(),
        "role": get_role(),
        "data_dir": get_data_dir(),
        "log_dir": get_log_dir(),
        "runtime_flavor": RUNTIME_FLAVOR,
        "runtime_dir": str(runtime_dir.resolve()),
        "runtime_exe": str(runtime_exe.resolve()),
    }
