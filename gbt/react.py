"""
react.py — ReAct Agent (推理+行动)
基于 hello-agents ReActAgent 模式
Thought → Action → Observation 循环
"""

import re
from typing import Optional, List, Tuple
from .llm import GBTLLM
from .tool import ToolRegistry
from .message import Message


# ── ReAct提示模板 ──
REACT_PROMPT = """你是一个具备推理和行动能力的AI助手。

## 可用工具
{tools}

## 工作流程
请严格按以下格式回应，每次只执行一个步骤：

Thought: 思考过程，分析问题、拆解任务、规划行动。
Action: 行动，格式:
- `{{tool_name}}[{{input}}]` - 调用工具
- `Finish[最终答案]` - 有足够信息时给出最终答案

## 重要
1. 每次回应必须包含Thought和Action
2. 工具调用格式: 工具名[参数]
3. 只有确信有足够信息时才用Finish
4. 信息不够就继续用工具

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始:"""


class ReActAgent:
    """ReAct推理-行动Agent"""

    def __init__(self, name: str, llm: GBTLLM, tool_registry: ToolRegistry,
                 system_prompt: Optional[str] = None,
                 max_steps: int = 5,
                 custom_prompt: Optional[str] = None):
        self.name = name
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.prompt_template = custom_prompt or REACT_PROMPT
        self._messages: List[Message] = []
        print(f"✅ [{self.name}] ReAct初始化, 最大步数={max_steps}")

    def run(self, input_text: str, **kwargs) -> str:
        """运行ReAct循环"""
        self.current_history = []
        step = 0
        print(f"\n🤖 [{self.name}] ReAct: {input_text[:80]}...")

        while step < self.max_steps:
            step += 1
            print(f"\n--- 第 {step} 步 ---")

            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc, question=input_text, history=history_str)

            messages = [{"role": "user", "content": prompt}]
            response = self.llm.invoke(messages, **kwargs)

            thought, action = self._parse_output(response)

            if thought:
                print(f"🤔 Thought: {thought[:100]}...")

            if action and action.startswith("Finish"):
                answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {answer[:100]}...")
                self._messages.append(Message(input_text, "user"))
                self._messages.append(Message(answer, "assistant"))
                return answer

            if action:
                tool_name, tool_input = self._parse_action(action)
                if tool_name:
                    print(f"🎬 Action: {tool_name}[{tool_input}]")
                    observation = self.tool_registry.execute(tool_name, tool_input)
                    print(f"👀 Observation: {observation[:100]}...")
                    self.current_history.append(f"Action: {action}")
                    self.current_history.append(f"Observation: {observation}")
                else:
                    self.current_history.append(f"Observation: 无效Action格式")

        fallback = "抱歉，在限定步数内无法完成任务。"
        self._messages.append(Message(input_text, "user"))
        self._messages.append(Message(fallback, "assistant"))
        return fallback

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 Thought 和 Action"""
        thought_m = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_m = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_m.group(1).strip() if thought_m else None
        action = action_m.group(1).strip() if action_m else None
        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 Action: tool_name[input]"""
        m = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        return (m.group(1), m.group(2)) if m else (None, None)

    def _parse_action_input(self, action_text: str) -> str:
        """解析 Finish[答案]"""
        m = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return m.group(1) if m else ""

    def add_message(self, msg: Message) -> None:
        self._messages.append(msg)
