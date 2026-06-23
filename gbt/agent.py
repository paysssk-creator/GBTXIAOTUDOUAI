"""
agent.py — Agent基类 (SimpleAgent)
基于 hello-agents SimpleAgent 模式
"""

import re
from typing import Optional, Iterator, List, Dict
from .message import Message, ConversationHistory, AgentConfig
from .llm import GBTLLM
from .tool import ToolRegistry


class SimpleAgent:
    """简单对话Agent — 支持可选工具调用"""

    def __init__(self, name: str, llm: GBTLLM,
                 system_prompt: Optional[str] = None,
                 config: Optional[AgentConfig] = None,
                 tool_registry: Optional[ToolRegistry] = None,
                 enable_tool_calling: bool = True):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt or "你是一个有用的AI助手。"
        self.config = config or AgentConfig(name=name)
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self._history = ConversationHistory()
        print(f"✅ [{self.name}] 初始化完成, 工具={'启用' if self.enable_tool_calling else '禁用'}")

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """运行Agent处理输入"""
        print(f"🤖 [{self.name}] 处理: {input_text[:80]}...")

        messages = []
        enhanced_sp = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_sp})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})

        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)
            self._history.add_user(input_text)
            self._history.add_assistant(response)
            return response

        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def _get_enhanced_system_prompt(self) -> str:
        """构建含工具信息的系统提示"""
        base = self.system_prompt
        if not self.enable_tool_calling or not self.tool_registry:
            return base
        tools_desc = self.tool_registry.get_tools_description()
        if not tools_desc or tools_desc == "暂无可用工具":
            return base
        return (base + "\n\n## 可用工具\n"
                "你可以使用以下工具：\n" + tools_desc + "\n\n"
                "## 工具调用格式\n"
                "需要工具时使用: `[TOOL_CALL:工具名:参数]`\n"
                "例如: `[TOOL_CALL:search:Python编程]`\n"
                "工具结果会自动插入，然后继续回答。")

    def _run_with_tools(self, messages: list, input_text: str,
                        max_iter: int, **kwargs) -> str:
        """多轮工具调用循环"""
        iteration = 0
        final = ""
        while iteration < max_iter:
            response = self.llm.invoke(messages, **kwargs)
            tool_calls = self._parse_tool_calls(response)
            if not tool_calls:
                final = response
                break
            print(f"🔧 检测到 {len(tool_calls)} 个工具调用")
            tool_results = []
            clean = response
            for call in tool_calls:
                result = self._execute_tool_call(call["tool_name"], call["params"])
                tool_results.append(result)
                clean = clean.replace(call["original"], "")
            messages.append({"role": "assistant", "content": clean})
            messages.append({"role": "user",
                "content": f"工具结果:\n{chr(10).join(tool_results)}\n请基于结果给出完整回答。"})
            iteration += 1

        if iteration >= max_iter and not final:
            final = self.llm.invoke(messages, **kwargs)

        self._history.add_user(input_text)
        self._history.add_assistant(final)
        print(f"✅ [{self.name}] 响应完成")
        return final

    def _parse_tool_calls(self, text: str) -> list:
        """解析 [TOOL_CALL:name:params] 格式"""
        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)
        return [{"tool_name": m[0].strip(), "params": m[1].strip(),
                 "original": f"[TOOL_CALL:{m[0]}:{m[1]}]"} for m in matches]

    def _execute_tool_call(self, tool_name: str, params: str) -> str:
        """执行单个工具调用"""
        if not self.tool_registry:
            return "❌ 未配置工具注册表"
        try:
            tool = self.tool_registry.get(tool_name)
            if not tool:
                return f"❌ 未找到工具: {tool_name}"
            # 智能参数解析
            param_dict = self._parse_params(tool_name, params)
            result = tool.run(param_dict)
            return f"🔧 {tool_name} 结果:\n{result}"
        except Exception as e:
            return f"❌ 工具调用失败: {e}"

    def _parse_params(self, tool_name: str, params: str) -> dict:
        """智能解析参数"""
        pd = {}
        if "=" in params:
            for pair in params.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    pd[k.strip()] = v.strip()
        else:
            pd = {"query" if tool_name in ("search","memory") else "input": params}
        return pd

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """流式运行"""
        print(f"🌊 [{self.name}] 流式: {input_text[:60]}...")
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})
        full = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full += chunk
            yield chunk
        self._history.add_user(input_text)
        self._history.add_assistant(full)

    def add_message(self, msg: Message) -> None:
        self._history.add(msg)

    def add_tool(self, tool) -> None:
        """添加工具"""
        if not self.tool_registry:
            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True
        self.tool_registry.register(tool.name, tool.description, tool.func, tool.parameters)

    def clear_history(self) -> None:
        self._history.clear()
