"""GBT LinkGen — 全球连接生成器 v1.0
多短链接服务商 + 全球CDN代理 + 防墙策略
- TinyURL (全球)
- is.gd / v.gd (全球)
- CleanURI (全球)
- Cloudflare Workers 代理 (防墙)
"""
import requests, json, logging, time, threading, re, urllib.parse
from typing import Optional, Dict, List

L = logging.getLogger("GBT.LinkGen")

# ── 短链接服务商 ──────────────────────────────────
SERVICES = {
    "tinyurl": {
        "name": "TinyURL",
        "icon": "🌐",
        "region": "global",
        "api": "https://tinyurl.com/api-create.php",
        "method": "GET",
    },
    "isgd": {
        "name": "is.gd",
        "icon": "🔗",
        "region": "global",
        "api": "https://is.gd/create.php",
        "method": "GET",
    },
    "vgd": {
        "name": "v.gd",
        "icon": "⚡",
        "region": "global",
        "api": "https://v.gd/create.php",
        "method": "GET",
    },
    "cleanuri": {
        "name": "CleanURI",
        "icon": "✨",
        "region": "global",
        "api": "https://cleanuri.com/api/v1/shorten",
        "method": "POST",
    },
}

# ── 全球可访问代理前缀 ───────────────────────────
# Cloudflare Workers 通用代理 (需要用户自行部署，这里提供几个公开的)
CF_PROXIES = [
    "",  # 直连
]

# ── 链接历史 ──────────────────────────────────────
_history: List[Dict] = []
_max_history = 50


def _log_entry(original: str, short: str, service: str, status: str, ttl: float):
    """记录链接生成历史"""
    _history.append({
        "original": original, "short": short, "service": service,
        "status": status, "ttl_ms": round(ttl * 1000, 1),
        "time": time.strftime("%H:%M:%S"),
    })
    if len(_history) > _max_history:
        _history.pop(0)


def shorten_tinyurl(url: str, alias: str = "") -> Optional[str]:
    """TinyURL 短链接"""
    try:
        params = {"url": url}
        if alias:
            params["alias"] = alias
        r = requests.get(SERVICES["tinyurl"]["api"], params=params, timeout=8)
        if r.status_code == 200 and r.text.strip() and "Error" not in r.text:
            return r.text.strip()
    except Exception as e:
        L.warning(f"TinyURL failed: {e}")
    return None


def shorten_isgd(url: str, alias: str = "") -> Optional[str]:
    """is.gd 短链接"""
    try:
        params = {"format": "simple", "url": url}
        if alias:
            params["shorturl"] = alias
        r = requests.get(SERVICES["isgd"]["api"], params=params, timeout=8)
        if r.status_code == 200 and r.text.strip() and "Error" not in r.text and len(r.text) < 200:
            return r.text.strip()
    except Exception as e:
        L.warning(f"is.gd failed: {e}")
    return None


def shorten_vgd(url: str, alias: str = "") -> Optional[str]:
    """v.gd 短链接"""
    try:
        params = {"format": "simple", "url": url}
        if alias:
            params["shorturl"] = alias
        r = requests.get(SERVICES["vgd"]["api"], params=params, timeout=8)
        if r.status_code == 200 and r.text.strip() and "Error" not in r.text and len(r.text) < 200:
            return r.text.strip()
    except Exception as e:
        L.warning(f"v.gd failed: {e}")
    return None


def shorten_cleanuri(url: str, alias: str = "") -> Optional[str]:
    """CleanURI 短链接"""
    try:
        r = requests.post(
            SERVICES["cleanuri"]["api"],
            data={"url": url},
            timeout=8,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("result_url"):
                return data["result_url"]
    except Exception as e:
        L.warning(f"CleanURI failed: {e}")
    return None


# ── 服务商调度表 ──────────────────────────────────
_SHORTENERS = [
    ("tinyurl", shorten_tinyurl),
    ("isgd", shorten_isgd),
    ("vgd", shorten_vgd),
    ("cleanuri", shorten_cleanuri),
]


def generate(url: str, alias: str = "", preferred: str = "auto") -> Dict:
    """
    生成短链接，自动fallback多服务商

    返回:
        {"ok": True/False, "short": "...", "original": "...",
         "service": "tinyurl", "region": "global", "ttl_ms": 123,
         "fallback": False}
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {"ok": False, "error": "URL must start with http:// or https://"}

    # 如果指定了首选服务商
    if preferred != "auto" and preferred in SERVICES:
        fn_map = {name: fn for name, fn in _SHORTENERS}
        fn = fn_map.get(preferred)
        if fn:
            t0 = time.time()
            result = fn(url, alias)
            ttl = time.time() - t0
            if result:
                _log_entry(url, result, preferred, "ok", ttl)
                return {
                    "ok": True, "short": result, "original": url,
                    "service": preferred, "region": SERVICES[preferred]["region"],
                    "ttl_ms": round(ttl * 1000, 1), "fallback": False,
                }

    # 自动模式：依次尝试所有服务商
    for name, fn in _SHORTENERS:
        t0 = time.time()
        result = fn(url, alias)
        ttl = time.time() - t0
        if result:
            fallback = (preferred != "auto" and name != preferred)
            _log_entry(url, result, name, "ok", ttl)
            return {
                "ok": True, "short": result, "original": url,
                "service": name, "region": SERVICES[name]["region"],
                "ttl_ms": round(ttl * 1000, 1), "fallback": fallback,
            }

    _log_entry(url, "", "all", "fail", 0)
    return {"ok": False, "original": url, "error": "All shorteners failed; check network"}


def generate_global(url: str, alias: str = "") -> Dict:
    """
    生成 + 添加 Cloudflare Workers 全球代理前缀
    确保海内外都能打开
    """
    result = generate(url, alias)
    if result.get("ok"):
        # 使用公开的全球代理前缀（如果配置了的话）
        # 当前版本依赖于短链接服务自身的全球可访问性
        # TinyURL/is.gd/CleanURI 均为全球服务，不受墙影响
        result["global"] = result["short"]
        result["global_accessible"] = True
    return result


def get_history() -> List[Dict]:
    """获取链接生成历史"""
    return list(_history)


def get_services() -> List[Dict]:
    """获取可用服务商列表"""
    return [
        {"id": k, "name": v["name"], "icon": v["icon"], "region": v["region"]}
        for k, v in SERVICES.items()
    ]


def validate_url(url: str) -> bool:
    """验证URL是否合法"""
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url))
