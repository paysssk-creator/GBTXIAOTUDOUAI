"""GBT Pro · gbt/api · Flask blueprint 注册中心
──────────────────────────────────────────────
把按子域拆分的 13 个 blueprint 注册到主 Flask app。
调用 register_all(app) 即可挂载全部 50 个 @bp.route。
"""

# 开发者: 自由的风
from __future__ import annotations

# 1) 共享状态
from . import _state  # noqa: F401  # 触发共享状态初始化

# 2) 所有 blueprint 子模块
from . import dash
from . import auth
from . import account
from . import llm
from . import market
from . import pilot
from . import connect
from . import audit
from . import strategy
from . import hacker
from . import mirror
from . import panel
from . import desktop
from . import payment  # T-010 FuturaPay 支付集成


# 3) 注册表（可被部署面板 / 探针枚举）
BLUEPRINTS = [
    ("dash",     dash.bp),
    ("auth",     auth.bp),
    ("account",  account.bp),
    ("llm",      llm.bp),
    ("market",   market.bp),
    ("pilot",    pilot.bp),
    ("connect",  connect.bp),
    ("audit",    audit.bp),
    ("strategy", strategy.bp),
    ("hacker",   hacker.bp),
    ("mirror",   mirror.bp),
    ("panel",    panel.bp),
    ("desktop",  desktop.bp),
    ("payment",  payment.bp),  # T-010 FuturaPay 支付集成
]


def register_all(app):
    """把全部 14 个 blueprint（13 + payment T-010）一次性注册到主 Flask app"""
    mounted = []
    for name, bp in BLUEPRINTS:
        app.register_blueprint(bp)
        mounted.append(name)
    return mounted


def list_routes():
    """列出全部 13 个 blueprint 名 + 路由条数，供探针 / 部署面板使用"""
    return [(name, len([r for r in bp.deferred_functions])) for name, bp in BLUEPRINTS]