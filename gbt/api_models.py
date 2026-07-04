# -*- coding: utf-8 -*-
"""
gbt/api_models.py — Pydantic API 输入校验模型

强制执行 OWASP (AS VS) 输入校验:
  - 类型检查
  - 长度限制
  - 模式约束
  - 防止注入攻击
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import re


class ReasonRequest(BaseModel):
    """POST /api/reason 请求体"""
    text: Optional[str] = Field(
        None, min_length=1, max_length=2000,
        description="用户输入文本",
    )
    question: Optional[str] = Field(
        None, min_length=1, max_length=2000,
        description="用户输入文本 (兼容字段)",
    )
    mode: Literal["quick", "deep", "chat", "chain"] = Field(
        "quick",
        description="推理模式: quick(关键词路由), deep(LLM推理), chat(对话), chain(链式)",
    )
    session_id: Optional[str] = Field(
        None,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="会话ID (可选)",
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="LLM 温度 (0-2)",
    )

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.replace("\x00", "")
        if len(v) > 2000:
            v = v[:2000]
        return v.strip()

    def model_post_init(self, __context):
        """合并 question → text"""
        if not self.text and self.question:
            object.__setattr__(self, "text", self.question)
        if not self.text:
            raise ValueError("text 或 question 字段不能都为空")

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 64:
            return v[:64]
        return v


class CapabilityRequest(BaseModel):
    """POST /api/capabilities 请求体"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="能力名称",
    )
    category: Optional[str] = Field(None, max_length=32)
    keywords: Optional[list[str]] = Field(None, max_length=100)
    priority: Optional[int] = Field(None, ge=1, le=10)
    handler: Optional[str] = Field(None, max_length=128)


class PingResponse(BaseModel):
    """健康检查响应"""
    status: Literal["ok", "degraded", "error"]
    service: str
    checks: Optional[dict] = None
    timestamp: str
