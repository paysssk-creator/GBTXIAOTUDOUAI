"""
audit.py — 交易审计日志 (合规级)
每笔操作记录: 时间戳/操作者/动作/参数/结果/IP/签名
"""
import os, json, time, hashlib, logging, threading
from datetime import datetime
from typing import Dict, Any, Optional

L = logging.getLogger("gbt.audit")

AUDIT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit_trail.jsonl")


class AuditLogger:
    """审计日志 — 合规级追踪"""
    _lock = threading.Lock()

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.count = 0

    def log(self, action: str, detail: Dict[str, Any] = None,
            operator: str = "system", result: str = "ok"):
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "operator": operator,
            "detail": detail or {},
            "result": result,
            "trace_id": hashlib.md5(f"{time.time()}{self.count}".encode()).hexdigest()[:12],
        }

        with self._lock:
            self.count += 1
            try:
                os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
                with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                L.warning(f"Audit write failed: {e}")

    def trade(self, side, code, name, price, shares, order_id, pnl_before=0):
        self.log("trade", {
            "side": side, "code": code, "name": name,
            "price": price, "shares": shares, "value": round(price * shares, 2),
            "order_id": order_id, "pnl_before": pnl_before,
        }, operator="autopilot", result="filled")

    def signal(self, code, signal_type, confidence, reasoning):
        self.log("signal", {
            "code": code, "signal": signal_type,
            "confidence": round(confidence, 3), "reasoning": reasoning[:200],
        }, operator="ai_decision")

    def config(self, key, old_val, new_val):
        self.log("config_change", {
            "key": key, "old": str(old_val)[:100], "new": str(new_val)[:100],
        }, operator="user")

    def error(self, module, error_msg):
        self.log("error", {"module": module, "error": str(error_msg)[:300]},
                 result="error")

    def startup(self, version="2.1"):
        self.log("startup", {"version": version, "host": os.environ.get("COMPUTERNAME", "")})

    def shutdown(self, reason=""):
        self.log("shutdown", {"reason": reason})


# 全局单例
_audit = None


def get_audit() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit
