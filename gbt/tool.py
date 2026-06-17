"""
tool.py — 工具注册表系统
基于 hello-agents ToolRegistry 模式
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, str] = field(default_factory=dict)  # {param_name: description}

    def run(self, params: Dict[str, Any] = None) -> str:
        """执行工具"""
        params = params or {}
        try:
            result = self.func(**params)
            return str(result) if result is not None else "执行完成"
        except Exception as e:
            return f"❌ 工具执行失败: {e}"

    def to_prompt_desc(self) -> str:
        """生成给LLM的工具描述"""
        params_str = ", ".join(f"{k}:{v}" for k, v in self.parameters.items())
        return f"- {self.name}({params_str}): {self.description}"


class ToolRegistry:
    """工具注册表 — 管理所有可用工具"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, func: Callable,
                 parameters: Dict[str, str] = None) -> None:
        """注册工具"""
        if name in self._tools:
            print(f"⚠️ 工具 '{name}' 已存在，将被覆盖")
        self._tools[name] = Tool(name=name, description=description,
                                 func=func, parameters=parameters or {})
        print(f"🔧 工具已注册: {name}")

    def register_function(self, name: str, description: str,
                          func: Callable) -> None:
        """注册函数为工具"""
        self.register(name, description, func)

    def unregister(self, name: str) -> bool:
        """移除工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def execute(self, name: str, input_str: str = "", params: Dict = None) -> str:
        """执行工具 (兼容ReAct的简单调用)"""
        tool = self.get(name)
        if not tool:
            return f"❌ 未找到工具: {name}"
        if params:
            return tool.run(params)
        # 简单输入模式
        return tool.run({"input": input_str})

    def execute_tool(self, name: str, input_str: str = "") -> str:
        """执行工具 (hello-agents兼容别名)"""
        return self.execute(name, input_str)

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具 (别名)"""
        return self.get(name)

    def list_tools(self) -> List[Tool]:
        """列出所有工具"""
        return list(self._tools.values())

    def get_tools_description(self) -> str:
        """生成工具描述文本 (给LLM用)"""
        if not self._tools:
            return "暂无可用工具"
        lines = []
        for name, tool in self._tools.items():
            params = ", ".join(f"{k}:{v}" for k, v in tool.parameters.items())
            lines.append(f"- {name}({params}): {tool.description}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
