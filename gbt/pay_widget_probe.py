# 开发者: 自由的风
"""pay_widget_probe.py — FuturaPay widget 三层可达性探测

# 用户铁律
- 地区差异时自动调节（同一 widget URL 在不同地区/网络可达性自动适配）
- 仅支付模块（T-010），绝不触及其他模块

L1 直连 requests/urllib
L2 curl_cffi 伪造 Chrome JA3
L3 playwright 真头浏览器 + 住宅 IP 代理（可选）
"""

import os, json, time, logging
from urllib.parse import urlparse


_LOG = logging.getLogger("gbt.pay_widget_probe")
if not _LOG.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(name)s] %(levelname)s · %(message)s"))
    _LOG.addHandler(_h)
    _LOG.setLevel(logging.INFO)


CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _force_layer() -> int:
    """用户演练可能强制锁层：GBT_PAYMENT_FORCE_LAYER=0/1/2/3"""
    raw = os.environ.get("GBT_PAYMENT_FORCE_LAYER", "0").strip()
    try:
        v = int(raw)
    except Exception:
        v = 0
    return v


def _probe_l1(url: str, timeout: int = 6) -> dict:
    """L1 直连 — 同步 urllib/requests"""
    t = time.time()
    try:
        import requests
        r = requests.get(url, timeout=timeout, stream=True, allow_redirects=True,
                         headers={"User-Agent": CHROME_UA,
                                  "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"})
        r.close()
        latency_ms = int((time.time() - t) * 1000)
        ok = (r.status_code < 500)
        return {"layer": 1, "ok": ok, "status": r.status_code,
                "latency_ms": latency_ms, "evidence": f"HTTP {r.status_code} in {latency_ms}ms"}
    except Exception as e:
        return {"layer": 1, "ok": False, "status": 0, "latency_ms": int((time.time() - t) * 1000),
                "evidence": f"L1 直连失败：{e}"}


def _probe_l2(url: str, timeout: int = 8) -> dict:
    """L2 curl_cffi — 伪造 Chrome JA3 fingerprint"""
    t = time.time()
    try:
        from curl_cffi import requests as cc_requests
        r = cc_requests.get(url, timeout=timeout,
                            impersonate="chrome124",
                            allow_redirects=True)
        latency_ms = int((time.time() - t) * 1000)
        ok = (r.status_code < 500)
        return {"layer": 2, "ok": ok, "status": r.status_code,
                "latency_ms": latency_ms, "evidence": f"HTTP {r.status_code} via curl_cffi chrome124 in {latency_ms}ms"}
    except Exception as e:
        return {"layer": 2, "ok": False, "status": 0, "latency_ms": int((time.time() - t) * 1000),
                "evidence": f"L2 curl_cffi 失败：{e}"}


def _probe_l3(url: str, timeout: int = 30) -> dict:
    """L3 playwright — 真头浏览器（仅在 install 后可用）"""
    t = time.time()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(user_agent=CHROME_UA,
                                          viewport={"width": 1280, "height": 800})
                page = ctx.new_page()
                r = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                status = r.status if r else 0
                latency_ms = int((time.time() - t) * 1000)
                ok = (status < 500)
                evidence = f"playwright headless=ok, status={status} in {latency_ms}ms"
            finally:
                browser.close()
        return {"layer": 3, "ok": ok, "status": status,
                "latency_ms": latency_ms, "evidence": evidence}
    except ImportError:
        return {"layer": 3, "ok": False, "status": 0, "latency_ms": int((time.time() - t) * 1000),
                "evidence": "L3 playwright 未安装 (pip install playwright && playwright install chromium)"}
    except Exception as e:
        return {"layer": 3, "ok": False, "status": 0, "latency_ms": int((time.time() - t) * 1000),
                "evidence": f"L3 playwright 失败：{e}"}


def probe_widget(url: str, force_layer: int = 0) -> dict:
    """三层降级链探测，返回最快成功的层级结果；全失败返回最后层级结果

    Args:
        url: widget URL（来自 gbt.pay_futurapay.generate_payment_link）
        force_layer: 0=auto / 1=L1 / 2=L2 / 3=L3

    Returns:
        {"layer", "ok", "status", "latency_ms", "evidence", "all_layers": [...]}
    """
    force = force_layer or _force_layer()
    if urlparse(url).hostname in ("", None):
        return {"layer": 0, "ok": False, "status": 0, "latency_ms": 0, "evidence": "URL 非法"}

    layers = [
        (1, _probe_l1) if force in (0, 1) else None,
        (2, _probe_l2) if force in (0, 2) else None,
        (3, _probe_l3) if force in (0, 3) else None,
    ]
    layers = [l for l in layers if l]

    if not layers:
        return {"layer": 0, "ok": False, "status": 0, "latency_ms": 0,
                "evidence": "GBT_PAYMENT_FORCE_LAYER 错误：仅 0/1/2/3"}

    attempts = []
    if force == 0:
        # 自动模式：每层试一次，成功的层返回
        for layer_id, fn in layers:
            r = fn(url)
            attempts.append(r)
            if r.get("ok"):
                # 注意：必须拷贝 attempts 并剥离 inner all_layers，避免 r→all_layers→[r] 自循环
                r["all_layers"] = [{k: v for k, v in a.items() if k != "all_layers"} for a in attempts]
                _LOG.info("Widget OK in layer %d · %s", layer_id, r.get("evidence", ""))
                return r
        # 全失败
        last = attempts[-1]
        last["all_layers"] = [{k: v for k, v in a.items() if k != "all_layers"} for a in attempts]
        _LOG.warning("Widget 全层失败：%s", [a.get("evidence") for a in attempts])
        return last
    else:
        # 强制某层
        layer_id, fn = layers[0]
        r = fn(url)
        # 强制模式：all_layers 只有一项，是当前层的剥离版
        r["all_layers"] = [{k: v for k, v in r.items() if k != "all_layers"}]
        return r
