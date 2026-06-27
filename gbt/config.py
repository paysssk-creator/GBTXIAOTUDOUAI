"""
gbt/config.py — 全局运行时配置

所有可能需要在运行时切换的开关统一放在这里，
避免散落在各模块中读取环境变量。
"""
import os

# 自动授权：开启后 AI 执行交易/操控电脑等动作时不再进入安全模拟模式
# 注意：涉及真实资金风险，请仅在模拟账户或充分理解风险后开启
AUTO_AUTHORIZE = os.environ.get("GBT_AUTO_AUTHORIZE", "0").lower() in ("1", "true", "yes", "on")


def set_auto_authorize(enabled: bool) -> bool:
    """运行时切换自动授权开关。"""
    global AUTO_AUTHORIZE
    AUTO_AUTHORIZE = enabled
    os.environ["GBT_AUTO_AUTHORIZE"] = "1" if enabled else "0"
    return AUTO_AUTHORIZE


def get_auto_authorize() -> bool:
    return AUTO_AUTHORIZE
