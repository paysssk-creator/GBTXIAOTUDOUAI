# 开发者: 自由的风
"""gbt/api/payment.py — FuturaPay 支付蓝图

端点：
  GET  /api/payment/status    系统侧配置状态 + 套餐 + 速率
  GET  /api/payment/link      生成加密 widget URL + 三层可达性探测
  POST /api/payment/webhook   接收 FuturaPay 异步回调（HMAC 验签可选）
  GET  /api/payment/orders    列出当前用户最近订单（审计友好）

# 用户铁律
- 密钥不入库，打包三层排除 — pay_futurapay 模块化锁住
- 锁本机账户、不接受修改 — payment_lock.py 守护
- 所有支付方式 + 自动链接 + 教用户付款 — 前端在 layout.html
"""

import os, io, json, time, hashlib, secrets, datetime, logging
from flask import Blueprint, jsonify, request, Response

import gbt.pay_futurapay as pf
import gbt.payment_lock as pl
from gbt.pay_widget_probe import probe_widget
from gbt.api.llm import _resolve_token_user

_LOG = logging.getLogger("gbt.api.payment")
if not _LOG.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(name)s] %(levelname)s · %(message)s"))
    _LOG.addHandler(_h)
    _LOG.setLevel(logging.INFO)


bp = Blueprint("payment", __name__)


def _removed_response():
    return jsonify({
        "ok": False,
        "removed": True,
        "error": "付费模块已下线，当前版本仅保留电脑操控与自主操盘主能力"
    }), 410

PROJECT_ROOT = os.environ.get("GBT_PROJECT_ROOT", "").strip() or os.getcwd()
DATA_ROOT = os.environ.get("GBT_DATA_DIR", "").strip() or os.path.join(PROJECT_ROOT, "data")
PAY_ROOT = os.path.join(DATA_ROOT, "pay")
ORDER_DIR = os.path.join(PAY_ROOT, "orders")
AUDIT_DIR = os.path.join(DATA_ROOT, "audit")
for d in (DATA_ROOT, PAY_ROOT, ORDER_DIR, AUDIT_DIR):
    os.makedirs(d, exist_ok=True)


# ─────────── 状态 / 配置 / 套餐 / 速率 ───────────
@bp.route("/api/payment/status")
def payment_status():
    return _removed_response()


# ─────────── 生成支付链接（核心） ───────────
@bp.route("/api/payment/link", methods=["GET", "POST"])
def payment_link():
    return _removed_response()


def _persist_order(user: str, res: dict, customer: dict):
    """订单持久化 + 审计"""
    p = os.path.join(ORDER_DIR, f"{res['customer_transaction_id']}.json")
    rec = {
        "customer_transaction_id": res["customer_transaction_id"],
        "user": user,
        "amount_cents": res["amount_cents"],
        "currency": res["currency"],
        "tokens": res["tokens"],
        "expires_at": res["expires_at"],
        "customer": customer,
        "status": "pending",
        "created_at": int(time.time()),
        "widget_url_base": res.get("widget_url_base"),
        "payment_url": res.get("url", ""),
        "payment_mode": "hosted_widget",
        "all_methods_via_widget": True,
    }
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _LOG.error("订单持久化失败：%s", e)
    # 审计
    _audit("link_generated", rec)


# ─────────── widget 探测（用前端按钮触发） ───────────
@bp.route("/api/payment/probe", methods=["POST"])
def payment_probe():
    return _removed_response()


# ─────────── webhook 回调 ───────────
@bp.route("/api/payment/webhook", methods=["POST"])
def payment_webhook():
    return _removed_response()


# ─────────── 订单列表（前端调试用） ───────────
@bp.route("/api/payment/orders")
def payment_orders():
    return _removed_response()


@bp.route("/api/payment/orders/<ctx_id>")
def payment_order_detail(ctx_id):
    return _removed_response()


@bp.route("/api/payment/qr/<ctx_id>")
def payment_order_qr(ctx_id):
    return _removed_response()


def _qr_svg_fallback(text: str, size: int = 220) -> str:
    """最差情况：用纯文本占位的 SVG，前端可继续显示而不破坏布局。"""
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<rect width="100%" height="100%" fill="#0f172a"/>'
        f'<rect x="6" y="6" width="{size-12}" height="{size-12}" fill="none" stroke="#22d3ee" stroke-width="2"/>'
        f'<text x="50%" y="42%" text-anchor="middle" fill="#22d3ee" font-family="monospace" font-size="14" font-weight="bold">扫码支付</text>'
        f'<text x="50%" y="56%" text-anchor="middle" fill="#e2e8f0" font-family="monospace" font-size="10">二维码引擎不可用</text>'
        f'<text x="50%" y="68%" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="9">请复制链接打开</text>'
        f'<text x="50%" y="86%" text-anchor="middle" fill="#cbd5e1" font-family="monospace" font-size="8">{(safe or "")[:60]}</text>'
        f'</svg>'
    )


# ─────────── 辅助 ───────────
def _audit(event: str, payload: dict):
    p = os.path.join(AUDIT_DIR, "futurapay.jsonl")
    try:
        rec = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "event": event,
            "user": os.environ.get("USERNAME", "?"),
            **payload,
        }
        # 防止整个 customer 流入审计日志
        if event != "link_generated" and "customer" in payload:
            rec["customer"] = {k: payload["customer"].get(k, "")[:8] + "***" for k in payload["customer"]}
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        _LOG.error("审计写失败：%s", e)


# 修补 pf（如果不存在 is_live_disabled）
if not hasattr(pf, "is_live_disabled"):
    def _isd():
        return (os.environ.get("FUTURAPAY_PAYMENT_DISABLED", "false").lower() == "true")
    pf.is_live_disabled = _isd
