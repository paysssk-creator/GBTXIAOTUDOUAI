"""gbt/templates/__init__.py
T-004 · 模板拼装包入口。
开发者: 自由的风
"""
from .composer import compose_dash_html, partials_summary, PARTIAL_NAMES

__all__ = ["compose_dash_html", "partials_summary", "PARTIAL_NAMES"]
