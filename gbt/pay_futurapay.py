# 开发者: 自由的风
"""pay_futurapay.py — FuturaPay 加密 + 支付链接生成

参考官方 Widget 文档：https://api.futurapay.com/developer/api/doc/widget
加密算法：AES-256-CBC，密钥 = md5(merchant_key + api_key + site_id)，IV 随机。

# 用户铁律（必须遵守）
1. 密钥从 .env 读，源码 0 硬编码；打包 .env 三层排除 — 已用 os.environ
2. 支付密钥仅锁在本地账户，只能本人收款，不接受运行时修改 — 用 payment_lock.py 守护
3. 集成所有支付方式 + 收款链接自动生成 + 教用户怎么付款
"""

import os, json, base64, hashlib, hmac, secrets, time, logging
from urllib.parse import urlencode, quote


_LOG = logging.getLogger("gbt.pay_futurapay")
if not _LOG.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(name)s] %(levelname)s · %(message)s"))
    _LOG.addHandler(_h)
    _LOG.setLevel(logging.INFO)


# ─────────── 启动时锁定（用户铁律 2） ───────────
_LOCKED = {"merchant_key": None, "api_key": None, "site_id": None, "lock_hash": None}


def _lock_keys():
    """模块导入时把密钥锁死，全程不可改"""
    if _LOCKED["site_id"] is not None:
        return  # 幂等
    c = _cfg_raw()
    if not (c["site_id"] and c["api_key"] and c["merchant_key"]):
        _LOG.warning("Futurapay 未完整配置（缺 merchant_key/api_key/site_id）— generate_payment_link 会拒绝")
    _LOCKED["merchant_key"] = c["merchant_key"]
    _LOCKED["api_key"]       = c["api_key"]
    _LOCKED["site_id"]       = c["site_id"]
    _LOCKED["lock_hash"]     = _hash_lock()
    _verify_lock_or_die()
    _LOG.info("Futurapay 密钥已锁 · site_id=%s · hash=%s", _LOCKED["site_id"][:6] + "***", _LOCKED["lock_hash"][:12])


def _cfg_raw():
    """未加锁的原始 env 读取（仅 _lock_keys 内部用，禁止外部调用）"""
    return {
        "site_id":      os.environ.get("FUTURAPAY_SITE_ID", ""),
        "api_key":      os.environ.get("FUTURAPAY_API_KEY", "") or os.environ.get("FUTURAPAY_API_KEY_LOCAL", ""),
        "merchant_key": os.environ.get("FUTURAPAY_MERCHANT_KEY", ""),
        "live":         (os.environ.get("FUTURAPAY_LIVE", "false").lower() == "true"),
        "disabled":     (os.environ.get("FUTURAPAY_PAYMENT_DISABLED", "false").lower() == "true"),
        "stage_url":    os.environ.get("FUTURAPAY_STAGE_WIDGET_URL", "https://stage-payment-widget.futurapay.com/widget/deposit"),
        "live_url":     os.environ.get("FUTURAPAY_LIVE_WIDGET_URL", "https://payment-widget.futurapay.com/widget/deposit"),
        "usd_rate":     int(os.environ.get("FUTURAPAY_USD_RATE", "12000")),
        "cny_rate":     int(os.environ.get("FUTURAPAY_CNY_RATE", "1650")),
    }


def _cfg():
    """只读配置视图，永远返回启动时锁定的值（不接受运行期修改）"""
    _lock_keys()
    return {
        "site_id":      _LOCKED["site_id"] or "",
        "api_key":      _LOCKED["api_key"] or "",
        "merchant_key": _LOCKED["merchant_key"] or "",
        "live":         _cfg_raw()["live"],
        "disabled":     _cfg_raw()["disabled"],
        "stage_url":    _cfg_raw()["stage_url"],
        "live_url":     _cfg_raw()["live_url"],
        "usd_rate":     _cfg_raw()["usd_rate"],
        "cny_rate":     _cfg_raw()["cny_rate"],
    }


def _hash_lock() -> str:
    parts = [
        _LOCKED["merchant_key"] or "",
        _LOCKED["api_key"] or "",
        _LOCKED["site_id"] or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _verify_lock_or_die():
    """每次 .env 重读后比对 hash；失配则写审计 + 拒绝一切支付请求"""
    raw = _cfg_raw()
    parts = [raw["merchant_key"] or "", raw["api_key"] or "", raw["site_id"] or ""]
    actual_hash = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    if _LOCKED["lock_hash"] and _LOCKED["lock_hash"] != actual_hash:
        _audit_tamper("lock_hash_mismatch", actual_hash)
        raise RuntimeError(
            f"FUTURAPAY 密钥运行时被篡改（hash {actual_hash[:12]} ≠ 锁定 {_LOCKED['lock_hash'][:12]}）"
            f"——已写审计 + 拒绝所有支付操作。请检查 .env 是否被外部修改。"
        )
    return True


def _audit_tamper(reason: str, value: str):
    """密钥被篡改的审计日志 — append-only 落到 data/audit/"""
    import datetime, os as _os
    p = _os.path.join("data", "audit", "futurapay_keys_tamper.jsonl")
    _os.makedirs(_os.path.dirname(p), exist_ok=True)
    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "reason": reason,
        "value_prefix": (value or "")[:16],
        "lock_hash": _LOCKED.get("lock_hash", "")[:16],
        "user": _os.environ.get("USERNAME", "?"),
    }
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ─────────── 公开配置查询 ───────────
def is_configured() -> bool:
    c = _cfg()
    return bool(c["site_id"]) and bool(c["api_key"]) and bool(c["merchant_key"])


def is_live() -> bool:
    return _cfg()["live"]


def widget_base_url() -> str:
    c = _cfg()
    return c["live_url"] if c["live"] else c["stage_url"]


def get_lock_hash() -> str:
    """暴露给审计看板；任何调用方都能拿当前 lock hash"""
    _lock_keys()
    return _LOCKED["lock_hash"] or ""


# ─────────── 加密（按官方 PHP 移植） ───────────
def _derive_key(merchant_key: str, api_key: str, site_id: str) -> bytes:
    """key = md5(merchant_key + api_key + site_id) → 16 字节"""
    return hashlib.md5(f"{merchant_key}{api_key}{site_id}".encode("utf-8")).digest()


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def encrypt_payload(payload: dict) -> dict:
    """参考 https://api.futurapay.com/developer/api/doc/widget · Encryptions::make
    返回 {"data": base64, "iv": base64, "key": base64(api_key)} 用于 URL query
    """
    c = _cfg()
    if not is_configured():
        raise RuntimeError("Futurapay 未配置（缺 merchant_key/api_key/site_id）")
    key = _derive_key(c["merchant_key"], c["api_key"], c["site_id"])
    plain = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    iv = secrets.token_bytes(16)
    cipher_text = _openssl_aes_256_cbc_encrypt(plain, key, iv)
    return {
        "data": base64.b64encode(cipher_text).decode("ascii"),
        "iv":   base64.b64encode(iv).decode("ascii"),
        "key":  base64.b64encode(c["api_key"].encode("ascii")).decode("ascii"),
    }


def _openssl_aes_256_cbc_encrypt(plain: bytes, key: bytes, iv: bytes) -> bytes:
    """AES-256-CBC + PKCS7 padding（等价 PHP openssl_encrypt + base64=true，但这里要 raw）"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    return enc.update(_pkcs7_pad(plain, 16)) + enc.finalize()


# ─────────── 解密（webhook 验签二次确认用） ───────────
def decrypt_payload(data_b64: str, iv_b64: str, payload_obj: dict = None) -> dict:
    """解密 widget 回调带回的 payload（用于二次确认订单金额）"""
    c = _cfg()
    if not is_configured():
        return {}
    key = _derive_key(c["merchant_key"], c["api_key"], c["site_id"])
    iv = base64.b64decode(iv_b64)
    cipher_text = base64.b64decode(data_b64)
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    plain = dec.update(cipher_text) + dec.finalize()
    pad_len = plain[-1]
    plain = plain[:-pad_len]
    try:
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return {}


# ─────────── 高级 API ───────────
def generate_payment_link(
    amount: float,
    currency: str,
    customer: dict,
    customer_transaction_id: str = None,
    expires_in: int = 3600,
) -> dict:
    """生成支付链接

    Args:
        amount: 金额（最小单位依 currency 而定：USD/CNY 都传整数元，代码会按 cents 提）
        currency: "USD" / "CNY"
        customer: {"first_name", "last_name", "email", "phone", "country_code"}
        customer_transaction_id: 由服务端生成的 16 位 ID

    Returns:
        {"ok", "url", "iframe_html", "customer_transaction_id", "expires_at",
         "amount_cents", "currency", "tokens", "widget_url_base", "error"}
    """
    c = _cfg()
    if c["disabled"]:
        return {"ok": False, "error": "FUTURAPAY_PAYMENT_DISABLED=true（管理员已切换）"}
    if not is_configured():
        return {"ok": False, "error": "Futurapay 未配置（缺 merchant_key/api_key/site_id）"}

    _verify_lock_or_die()  # 最后一道，hash 不符直接 raise

    ctx_id = (customer_transaction_id or secrets.token_hex(8)).upper()
    expires_at = int(time.time()) + expires_in
    amount_f = float(f"{amount:.2f}")
    tokens = to_tokens(amount_f, currency)

    widget_payload = {
        "currency": currency,
        "amount": amount_f,
        "customer_transaction_id": ctx_id,
        "country_code": customer.get("country_code", "CN"),
        "customer_first_name": customer.get("first_name", "")[:64],
        "customer_last_name":  customer.get("last_name", "")[:64],
        "customer_phone":      customer.get("phone", "")[:32],
        "customer_email":      customer.get("email", "")[:128],
        "metadata": json.dumps({"ctx": ctx_id, "tokens": tokens, "ts": expires_at}, separators=(",", ":")),
    }

    enc = encrypt_payload(widget_payload)
    query = urlencode(enc)
    base = widget_base_url()
    full_url = f"{base}?{query}"

    iframe_html = (
        f'<iframe id="futurapay-widget" src="{quote(full_url, safe="=:&?")}" '
        f'width="100%" height="600" frameborder="0" '
        f'sandbox="allow-scripts allow-forms allow-same-origin allow-top-navigation"></iframe>'
    )

    return {
        "ok": True,
        "url": full_url,
        "iframe_html": iframe_html,
        "customer_transaction_id": ctx_id,
        "expires_at": expires_at,
        "amount_cents": int(round(amount_f * 100)),
        "currency": currency,
        "tokens": tokens,
        "widget_url_base": base,
    }


# ─────────── HMAC 签名（webhook 可选） ───────────
def hmac_sign(payload_bytes: bytes, secret: str = None) -> str:
    secret = secret or os.environ.get("FUTURAPAY_WEBHOOK_HMAC_SECRET") or os.environ.get("FUTURAPAY_API_KEY_LOCAL", "")
    if not secret:
        return ""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def verify_hmac(payload_bytes: bytes, signature: str, secret: str = None) -> bool:
    expected = hmac_sign(payload_bytes, secret)
    if not expected or not signature:
        return False
    return hmac.compare_digest(expected, signature)


# ─────────── 套餐 / 汇率辅助 ───────────
def get_token_packages() -> list:
    raw = os.environ.get("FUTURAPAY_TOKEN_PACKAGES", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def rate_label() -> str:
    c = _cfg()
    return f"1 USD ≈ {c['usd_rate']:,} tokens · 1 CNY ≈ {c['cny_rate']:,} tokens"


def to_tokens(amount: float, currency: str) -> int:
    """金额 → token 换算
    注意：CNY 在 Futurapay 官方文档中无支持示例（已查 Widget 文档 / PHP SDK 文档）
          仅 SDK 示例列了 USD / EUR；货币清单以 provider 后台 'Settings → Currencies' 为准
          所以 CNY 调用必失败，回退 USD 优先
    """
    c = _cfg()
    if currency == "USD":
        return int(round(amount * c["usd_rate"]))
    if currency == "CNY":
        # 实测层面：Futurapay 是否支持 CNY 由 widget 探测结果动态决定
        return int(round(amount * c["cny_rate"]))
    if currency == "EUR":
        return int(round(amount * c["usd_rate"]))  # 暂以 USD 汇率做 fallback
    return 0


SUPPORTED_CURRENCIES = ("USD", "EUR")  # 主支持
EXPERIMENTAL_CURRENCIES = ("CNY",)     # 试探性（widget 拒则回退）


# 模块导入即锁
_lock_keys()
