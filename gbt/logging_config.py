# -*- coding: utf-8 -*-
"""
gbt/logging_config.py — 结构化日志配置

生产标准:
  - JSON 格式输出 (可被 ELK/Loki/Datadog 解析)
  - 多级别控制 (DEBUG/INFO/WARNING/ERROR)
  - 自动包含模块名、行号、进程信息
"""
import logging, json, sys, os, time
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON 结构化日志格式化器"""

    _SENSITIVE_KEYS = {"api_key", "password", "token", "secret", "authorization"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "pid": os.getpid(),
            "thread": record.threadName,
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        # 清理敏感信息
        msg_lower = log_entry["message"].lower()
        for key in self._SENSITIVE_KEYS:
            if key in msg_lower:
                log_entry["message"] = "[REDACTED: contains sensitive key]"
                break

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ReadableFormatter(logging.Formatter):
    """开发环境可读格式 (非JSON)"""
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        level = record.levelname[:4]
        return f"[{ts}] {level:4s} [{record.name:16s}] {record.getMessage()}"


def setup_logging(level: str = "INFO", json_mode: bool = False):
    """
    初始化全局日志配置

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        json_mode: True=JSON结构化, False=可读格式
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有 handler
    for h in list(root.handlers):
        root.removeHandler(h)

    # 控制台输出
    handler = logging.StreamHandler(sys.stderr)
    if json_mode:
        fmt = StructuredFormatter()
    else:
        fmt = ReadableFormatter()
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # 文件输出 (JSON 格式)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"gbt_{datetime.now().strftime('%Y%m%d')}.log")
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(StructuredFormatter())
    root.addHandler(file_handler)

    # 降低第三方库噪音
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    root.info(f"Logging initialized | json={json_mode} | file={log_file}")
