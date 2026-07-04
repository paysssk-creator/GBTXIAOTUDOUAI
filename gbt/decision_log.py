"""decision_log.py · GBT Pro 决策日志 · 开发者: 自由的风
按用户铁律"双轨日志（审计+决策）"—— audit 记录"发生了什么"，decision 记录"为什么这样做"。
所有关键路径（支付 / 充值 / 风控 / 策略执行）必须写决策日志，便于事后追溯。
"""
import json, time
from pathlib import Path

ROOT = Path(r"c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI")
DECISION_LOG = ROOT / "data" / "audit" / "decision.jsonl"


def decide(category: str, action: str, rationale: str, payload: dict = None, level: str = "INFO"):
    """写决策日志
    Args:
        category: 决策类别（payment / risk / strategy / auth / market / system）
        action:   动作（grant / deny / refund / escalate / auto / manual）
        rationale: 决策依据（自然语言，便于人审）
        payload:  上下文（JSON-safe）
        level:    INFO / WARN / CRITICAL
    """
    entry = {
        "ts": int(time.time()),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "category": category,
        "action": action,
        "level": level,
        "rationale": rationale,
        "developer": "自由的风",
        "payload": payload or {},
    }
    DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DECISION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent(limit: int = 20):
    """读最近 N 条决策"""
    if not DECISION_LOG.exists():
        return []
    lines = DECISION_LOG.read_text(encoding="utf-8").strip().split("\n")
    out = []
    for ln in lines[-limit:]:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return list(reversed(out))


if __name__ == "__main__":
    # 演示：写几条决策
    decide("system", "audit_complete", "T-012 全量生产审计完成 6/10 通过", {"passed": 6, "failed": 2, "warn": 2})
    decide("payment", "cny_experimental_open", "用户决定试 CNY 收款 — 官方不支持但 widget 实测可走", {"currency": "CNY", "rate": 1650}, level="WARN")
    decide("security", "key_lock_init", "启动期 _lock_keys() 锁住 FUTURAPAY_* 到内存 + SHA256 hash", {"hash_prefix": "88f19a585523"})
    decide("market", "dual_source_fallback", "东财上游 502 时自动降级新浪 + 腾讯", {"primary": "eastmoney", "fallback_quote": "sina", "fallback_kline": "tencent"})
    decide("release", "block_on_no_packaging", "打包基建缺失 (Dockerfile / spec / NSIS) → 阻断生产发布", {"missing": ["Dockerfile", "desktop_app.spec", "build_exe.py"]}, level="CRITICAL")
    print(f"✅ 决策日志已写：{DECISION_LOG}")
    print()
    print("=== 最近决策 ===")
    for d in recent(5):
        print(f"  [{d['level']:8s}] {d['category']:10s} {d['action']:25s} — {d['rationale'][:60]}")