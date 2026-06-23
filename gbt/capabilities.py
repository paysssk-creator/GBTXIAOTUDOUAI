# -*- coding: utf-8 -*-
"""
capabilities.py — GBT capability registry v4
借鉴 open-strix 的 skill 组织方式：
- 每个能力拆分为 gbt/skills/<name>.py 独立模块
- 每个模块既能被 SmartRouter 统一调度
- 也能通过 `python -m gbt.skills.<name>` 独立运行
本文件负责把 skill 注册表同步到旧版 router，保持全部现有 API 兼容。
"""
import logging
from gbt.router import Capability, router
from gbt.skills import base, registry

L = logging.getLogger("GBT.Capabilities")

# Import all skill modules so they self-register into the skill registry.
# This makes every capability discoverable both by the central router and
# runnable standalone from the command line.
_SKILL_MODULES = [
    "gbt.skills.maximize",
    "gbt.skills.screenshot",
    "gbt.skills.screen_ocr",
    "gbt.skills.browser_open",
    "gbt.skills.web_search",
    "gbt.skills.stock_lookup",
    "gbt.skills.scan_market",
    "gbt.skills.watchlist",
    "gbt.skills.trade",
    "gbt.skills.system_status",
    "gbt.skills.watcher_check",
    "gbt.skills.account_query",
    "gbt.skills.notify",
    "gbt.skills.file_operation",
    "gbt.skills.code_exec",
    "gbt.skills.voice_speak",
    "gbt.skills.login_detect",
    "gbt.skills.precision_scrape",
    "gbt.skills.auto_pipeline",
]


def _import_skills():
    for mod in _SKILL_MODULES:
        try:
            __import__(mod)
            L.debug(f"Loaded skill module: {mod}")
        except Exception as e:
            L.warning(f"Failed to load skill module {mod}: {e}")


def _make_handler(skill):
    """Wrap a Skill instance into the legacy Capability handler signature."""
    def _handler(text):
        res = skill.run(text)
        return res.to_dict()
    return _handler


def register_all() -> int:
    """Register all discovered skills into the SmartRouter."""
    _import_skills()
    count = 0
    for name, skill in registry.skills.items():
        cap = Capability(
            name=skill.name,
            category=skill.category,
            description=skill.description,
            keywords=skill.keywords,
            handler=_make_handler(skill),
            priority=skill.priority,
            requires=skill.requires,
        )
        router.register(cap)
        count += 1
    L.info(f"Registered {count} capabilities from skill registry")
    return count


register_all()
