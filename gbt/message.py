"""
message.py — 消息数据结构
基于 hello-agents Message/Config 模式构建
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Message:
    """对话消息"""
    content: str
    role: str  # "system" | "user" | "assistant" | "tool"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转为 OpenAI 兼容格式"""
        msg = {"role": self.role, "content": self.content}
        if self.metadata:
            msg["metadata"] = self.metadata
        return msg

    def __repr__(self) -> str:
        preview = self.content[:60] + "..." if len(self.content) > 60 else self.content
        return f"Message(role={self.role}, content='{preview}')"


@dataclass
class ConversationHistory:
    """对话历史管理器"""
    messages: List[Message] = field(default_factory=list)
    max_turns: int = 20  # 最多保留轮次

    def add(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)
        self._trim()

    def add_user(self, content: str) -> None:
        """快捷添加用户消息"""
        self.add(Message(content=content, role="user"))

    def add_assistant(self, content: str) -> None:
        """快捷添加助手消息"""
        self.add(Message(content=content, role="assistant"))

    def add_system(self, content: str) -> None:
        """快捷添加系统消息"""
        self.add(Message(content=content, role="system"))

    def _trim(self) -> None:
        """裁剪历史，保留最近 max_turns 轮"""
        # 每轮 = user + assistant，保留 max_turns * 2 条
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

    def to_openai_format(self, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """转为 OpenAI API 兼容的消息列表"""
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def get_last(self, n: int = 1) -> List[Message]:
        """获取最后 n 条消息"""
        return self.messages[-n:] if self.messages else []

    def clear(self) -> None:
        """清空历史"""
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self):
        return iter(self.messages)


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str = "GBTAgent"
    max_steps: int = 10
    max_tool_iterations: int = 5
    temperature: float = 0.7
    max_tokens: int = 4096
    enable_streaming: bool = True
    enable_tool_calling: bool = True
    debug: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
