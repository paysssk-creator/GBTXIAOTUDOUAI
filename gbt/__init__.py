"""
GBT Agent Framework - AI原生Agent框架核心
"""

import sys, os
if sys.platform == 'win32':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass  # 非关键：编码设置失败不影响核心功能
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass  # 非关键：编码设置失败不影响核心功能

from .llm import GBTLLM
from .tool import ToolRegistry, Tool
from .agent import SimpleAgent, AgentConfig
from .message import Message, ConversationHistory
from .react import ReActAgent
from .memory import MemoryManager
from .evolve import EvolveEngine, EvolveReport, EvolveStep, run_evolve
from .guard import PreActionGuard, GuardReport, GuardStatus, \
    ScanSnapshot, FileScanItem, scan_all, guard_action, guard_deploy
from .mirror import MirrorSpace, MirrorPipeline, RealCodeValidator, \
    CodeIssue, IssueType, MirrorReport, scan_fakes, mirror_run
from .mcp import UniversalMCP, MCPServer, MCPResult, MCPStatus, get_mcp, call_mcp
from .reasoner import DeepReasoner, ReasonMode, ReasonResult, ReasonNode
from .winctl import WindowsController, WinResult, WinFeature, get_winctl

# ── 共享配置常量 ──
DEFAULT_PING_TARGET = "8.8.8.8"  # 网络连通性检测的缺省目标

__version__ = "1.5.0"
__all__ = [
    "GBTLLM", "ToolRegistry", "Tool",
    "SimpleAgent", "AgentConfig",
    "Message", "ConversationHistory",
    "ReActAgent", "MemoryManager",
    "EvolveEngine", "EvolveReport", "EvolveStep", "run_evolve",
    "PreActionGuard", "GuardReport", "GuardStatus",
    "ScanSnapshot", "FileScanItem",
    "scan_all", "guard_action", "guard_deploy",
    "MirrorSpace", "MirrorPipeline", "RealCodeValidator",
    "CodeIssue", "IssueType", "MirrorReport",
    "scan_fakes", "mirror_run",
    "UniversalMCP", "MCPServer", "MCPResult", "MCPStatus",
    "get_mcp", "call_mcp",
    "DeepReasoner", "ReasonMode", "ReasonResult", "ReasonNode",
    "WindowsController", "WinResult", "WinFeature", "get_winctl",
]
