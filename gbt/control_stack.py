from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys


@dataclass(frozen=True)
class ExternalControlStack:
    id: str
    name: str
    repo: str
    url: str
    branch: str
    sha: str
    role: str
    expected_paths: tuple[str, ...]
    supported_platforms: tuple[str, ...]

    @property
    def env_var(self) -> str:
        return f"GBT_CONTROL_STACK_{self.id.upper().replace('-', '_')}_ROOT"


_STACKS: tuple[ExternalControlStack, ...] = (
    ExternalControlStack(
        id="openinterpreter",
        name="Open Interpreter",
        repo="openinterpreter/openinterpreter",
        url="https://github.com/openinterpreter/openinterpreter",
        branch="main",
        sha="ac1b565c729e7a6192865e03301d81fa7c924025",
        role="open-model computer use and code execution",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux", "macos"),
    ),
    ExternalControlStack(
        id="omniparser",
        name="OmniParser",
        repo="microsoft/OmniParser",
        url="https://github.com/microsoft/OmniParser",
        branch="master",
        sha="b0d5c9f5701f7e2be4771872e6e928da77759df3",
        role="screen parsing and UI grounding",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux"),
    ),
    ExternalControlStack(
        id="self_operating_computer",
        name="Self-Operating Computer",
        repo="OthersideAI/self-operating-computer",
        url="https://github.com/OthersideAI/self-operating-computer",
        branch="main",
        sha="fac568eea7da5e24f8bc91bfc1211b65679177eb",
        role="multimodal browser and desktop action loop",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux", "macos"),
    ),
    ExternalControlStack(
        id="agent_s",
        name="Agent-S",
        repo="simular-ai/Agent-S",
        url="https://github.com/simular-ai/Agent-S",
        branch="main",
        sha="73ea17225bae73ab45d077cc442978d3ff8e286a",
        role="human-like computer use orchestration",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux", "macos"),
    ),
    ExternalControlStack(
        id="ufo",
        name="UFO",
        repo="microsoft/UFO",
        url="https://github.com/microsoft/UFO",
        branch="main",
        sha="b28183fd426452c6cb511627c9bd32a929f29406",
        role="Windows desktop automation agents",
        expected_paths=("README.md",),
        supported_platforms=("windows",),
    ),
    ExternalControlStack(
        id="cradle",
        name="Cradle",
        repo="BAAI-Agents/Cradle",
        url="https://github.com/BAAI-Agents/Cradle",
        branch="main",
        sha="d7752fccf890d8d3818cd1d435f3705f604a1339",
        role="general computer control and self-improvement",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux"),
    ),
    ExternalControlStack(
        id="os_copilot",
        name="OS-Copilot",
        repo="OS-Copilot/OS-Copilot",
        url="https://github.com/OS-Copilot/OS-Copilot",
        branch="main",
        sha="f720af8807e49a92dda64572d2c6bc6c0ac7ee7e",
        role="operating-system level embodied agent",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux"),
    ),
    ExternalControlStack(
        id="showui",
        name="ShowUI",
        repo="showlab/ShowUI",
        url="https://github.com/showlab/ShowUI",
        branch="main",
        sha="21ed7cb24be0cc877bb8352ee34d58a9aea2c876",
        role="vision-language GUI action model",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux"),
    ),
    ExternalControlStack(
        id="ui_tars_desktop",
        name="UI-TARS Desktop",
        repo="bytedance/UI-TARS-desktop",
        url="https://github.com/bytedance/UI-TARS-desktop",
        branch="main",
        sha="c2ad42e3eb9b27830db41a3e6f51ca7179d9b168",
        role="multimodal agent stack and desktop runtime",
        expected_paths=("README.md",),
        supported_platforms=("windows", "linux", "macos"),
    ),
)


def _platform_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _root_candidates(stack: ExternalControlStack) -> list[Path]:
    out: list[Path] = []
    env_root = os.environ.get(stack.env_var, "").strip()
    if env_root:
        out.append(Path(env_root))
    base = _project_root()
    out.append(base / "third_party" / "control_stacks" / stack.id)
    out.append(base / "vendor" / "control_stacks" / stack.id)
    dedup: list[Path] = []
    seen: set[str] = set()
    for item in out:
        key = str(item)
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


def _detect_stack_root(stack: ExternalControlStack) -> tuple[Path | None, str, list[str]]:
    for root in _root_candidates(stack):
        if not root.exists():
            continue
        found = [rel for rel in stack.expected_paths if (root / rel).exists()]
        if len(found) == len(stack.expected_paths):
            return root.resolve(), "snapshot_ready", found
        if found:
            return root.resolve(), "partial", found
        return root.resolve(), "unverified", []
    return None, "missing", []


def list_external_control_stacks() -> list[dict]:
    current_platform = _platform_name()
    items: list[dict] = []
    for stack in _STACKS:
        root, status, found = _detect_stack_root(stack)
        compatible = current_platform in stack.supported_platforms
        items.append({
            "id": stack.id,
            "name": stack.name,
            "repo": stack.repo,
            "url": stack.url,
            "branch": stack.branch,
            "sha": stack.sha,
            "role": stack.role,
            "status": status,
            "compatible": compatible,
            "supported_platforms": list(stack.supported_platforms),
            "root": str(root).replace("\\", "/") if root else None,
            "env_var": stack.env_var,
            "found_markers": found,
            "activation_mode": "native_first_optional_external",
        })
    return items


def build_control_stack_report() -> dict:
    items = list_external_control_stacks()
    current_platform = _platform_name()
    compatible = [item for item in items if item["compatible"]]
    snapshots = [item for item in compatible if item["status"] == "snapshot_ready"]
    recommended = ["native_desktop"]
    for preferred in ("ufo", "agent_s", "cradle", "ui_tars_desktop", "omniparser"):
        if any(item["id"] == preferred and item["status"] == "snapshot_ready" for item in compatible):
            recommended.append(preferred)
    return {
        "ok": True,
        "platform": current_platform,
        "primary_controller": "native_desktop",
        "fallback_policy": "native_first_optional_external",
        "atomic_policy": {
            "immutable_snapshots_only": True,
            "in_place_overwrite": False,
            "rollback_required": True,
        },
        "summary": {
            "total_external_stacks": len(items),
            "compatible_external_stacks": len(compatible),
            "snapshot_ready_external_stacks": len(snapshots),
        },
        "recommended_order": recommended,
        "stacks": items,
    }
