"""
GBT Agent Framework - AI原生Agent框架核心
按照 hello-agents 框架模式构建，为 GBT小土豆全能开发者 提供Agent大脑
"""

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
