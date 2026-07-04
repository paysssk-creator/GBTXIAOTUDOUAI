"""GBT Pro 镜像空间 — 顶层子包入口

把仓库 paysssk-creator/jingxiangduoweidukongjian 安装到 GBT Pro 自身。

用法：
    from gbt.mirror_space.bridge import (
        status, invoke_skill, build_module_registry,
        evolve, pipeline, latest_report, list_modules,
        active_skill_doc, safe_dry_run
    )
"""

# 开发者: 自由的风
from .bridge import (  # noqa: F401
    status,
    invoke_skill,
    invoke_orchestrator,
    build_module_registry,
    evolve,
    pipeline,
    latest_report,
    list_modules,
    active_skill_doc,
    safe_dry_run,
)

__all__ = [
    "status",
    "invoke_skill",
    "invoke_orchestrator",
    "build_module_registry",
    "evolve",
    "pipeline",
    "latest_report",
    "list_modules",
    "active_skill_doc",
    "safe_dry_run",
]

VERSION = "1.0.0"
PLUGIN_NAME = "mirror-space"
PLUGIN_REPO = "https://github.com/paysssk-creator/jingxiangduoweidukongjian"
