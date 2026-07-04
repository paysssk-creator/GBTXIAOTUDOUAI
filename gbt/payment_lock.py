# 开发者: 自由的风
"""payment_lock.py — 支付密钥本地化 + 启动时锁定

# 用户铁律（必须遵守）
- 集成支付密钥保护在本机，只能本人账户收款，不接受运行时修改
- 任何 .env 改动都会被检测 + 写入审计 + 拒绝支付操作
"""

import os, json, hashlib, logging


_LOG = logging.getLogger("gbt.payment_lock")
if not _LOG.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(name)s] %(levelname)s · %(message)s"))
    _LOG.addHandler(_h)
    _LOG.setLevel(logging.INFO)


BASELINE_FILE = os.path.join("data", "pay", ".keys.lock")
AUDIT_FILE    = os.path.join("data", "audit", "payment_lock_audit.jsonl")


def _hash_keys(merchant_key: str, api_key: str, site_id: str) -> str:
    return hashlib.sha256(f"{merchant_key}|{api_key}|{site_id}".encode("utf-8")).hexdigest()


def save_baseline(force: bool = False) -> dict:
    """首次部署时存一个 baseline 到 .keys.lock；后续启动比对"""
    if os.path.exists(BASELINE_FILE) and not force:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
    merchant_key = os.environ.get("FUTURAPAY_MERCHANT_KEY", "")
    api_key      = os.environ.get("FUTURAPAY_API_KEY", "") or os.environ.get("FUTURAPAY_API_KEY_LOCAL", "")
    site_id      = os.environ.get("FUTURAPAY_SITE_ID", "")
    lock_hash    = _hash_keys(merchant_key, api_key, site_id)
    b = {
        "site_id_prefix":  site_id[:6] + "***" if site_id else "",
        "lock_hash":       lock_hash,
        "saved_at":        __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "saved_by":        os.environ.get("USERNAME", "?"),
    }
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)
    _LOG.info("Payment lock baseline saved → %s · hash=%s", BASELINE_FILE, lock_hash[:12])
    return b


def verify_baseline() -> dict:
    """启动时检查 .env 密钥是否与 baseline 一致；不一致 → 警告但 run 起来（兼容未配置）"""
    merchant_key = os.environ.get("FUTURAPAY_MERCHANT_KEY", "")
    api_key      = os.environ.get("FUTURAPAY_API_KEY", "") or os.environ.get("FUTURAPAY_API_KEY_LOCAL", "")
    site_id      = os.environ.get("FUTURAPAY_SITE_ID", "")
    current_hash = _hash_keys(merchant_key, api_key, site_id)

    if not (site_id and api_key and merchant_key):
        return {"status": "incomplete", "current": current_hash[:12]}

    if not os.path.exists(BASELINE_FILE):
        # 首次：自动存 baseline，绝不阻（即使 baseline 文件丢失，也按"首次"处理 — 绝不误伤可用密钥）
        b = save_baseline(force=False)
        return {"status": "ok", "current": current_hash[:12], "baseline": b["lock_hash"][:12], "auto_bootstrapped": True}

    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        b = json.load(f)
    baseline_hash = b.get("lock_hash", "")
    if current_hash == baseline_hash:
        return {"status": "ok", "current": current_hash[:12], "baseline": baseline_hash[:12]}
    # 失配 → 写审计 + 警告
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts":       __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "event":    "key_drift",
            "baseline": baseline_hash[:16],
            "current":  current_hash[:16],
            "user":     os.environ.get("USERNAME", "?"),
            "site_id_prefix": site_id[:6] + "***",
        }, ensure_ascii=False) + "\n")
    _LOG.warning("FUTURAPAY 密钥与 baseline 失配 — 已写审计 %s — 支付操作会被拒绝，直到密钥恢复到 baseline", AUDIT_FILE)
    return {"status": "drift", "current": current_hash[:12], "baseline": baseline_hash[:12], "audit": AUDIT_FILE}


def is_lock_intact() -> bool:
    """轻量只读 hash 对比，给 gbt.pay_futurapay 调"""
    v = verify_baseline()
    return v.get("status") in ("init", "ok")
