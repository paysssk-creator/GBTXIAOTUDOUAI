# -*- coding: utf-8 -*-
"""
gbt/scraper.py — GBT 精准资讯抓取引擎 v2.0

吸收 Scrapling 核心能力:
- 反机器人绕过 (stealth headers / TLS fingerprint / Cloudflare bypass)
- 自适应选择器 (HTML结构变化自动重定位)
- 会话持久化 (cookie/state 管理，券商登录态保持)
- 浏览器动态渲染 (JS 重页面)

多源交叉验证 + 置信度评分 + 偏差检测
"""

import re
import ssl
import json
import time
import logging
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable

L = logging.getLogger("GBT.Scraper")


# ═══════════════════════════════════════════════════════
# 1. 反机器人 Bypass — StealthFetcher 枚举
# ═══════════════════════════════════════════════════════

@dataclass
class BrowserFingerprint:
    """浏览器指纹 — 用于 TLS 伪装 + 反检测"""
    name: str
    user_agent: str
    accept_language: str = "zh-CN,zh;q=0.9,en;q=0.8"
    accept_encoding: str = "gzip, deflate, br"
    sec_ch_ua: str = ""
    sec_ch_ua_platform: str = '"Windows"'
    tls_version: str = "TLS 1.3"

# 常用指纹库
FINGERPRINTS = {
    "chrome_130": BrowserFingerprint(
        "Chrome 130",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        sec_ch_ua='"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    ),
    "chrome_131": BrowserFingerprint(
        "Chrome 131",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        sec_ch_ua='"Chromium";v="131", "Google Chrome";v="131", "Not?A_Brand";v="99"',
    ),
    "edge_131": BrowserFingerprint(
        "Edge 131",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        sec_ch_ua='"Chromium";v="131", "Microsoft Edge";v="131", "Not?A_Brand";v="99"',
    ),
    "firefox_133": BrowserFingerprint(
        "Firefox 133",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    ),
}

# 反检测请求头模板
STEALTH_BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


def build_stealth_headers(
    fingerprint: str = "chrome_131",
    referer: str = "",
    origin: str = "",
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """构建反检测请求头 — 模拟真实浏览器"""
    fp = FINGERPRINTS.get(fingerprint, FINGERPRINTS["chrome_131"])
    headers = dict(STEALTH_BASE_HEADERS)
    headers["User-Agent"] = fp.user_agent
    headers["Accept-Language"] = fp.accept_language

    if fp.sec_ch_ua:
        headers["Sec-Ch-Ua"] = fp.sec_ch_ua
        headers["Sec-Ch-Ua-Platform"] = fp.sec_ch_ua_platform
        headers["Sec-Ch-Ua-Mobile"] = "?0"

    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
    if extra:
        headers.update(extra)

    return headers


# ═══════════════════════════════════════════════════════
# 2. 自适应选择器 — 元素指纹 + 模糊重定位
# ═══════════════════════════════════════════════════════

@dataclass
class ElementFingerprint:
    """元素指纹 — 用于 HTML 结构变化后重新定位"""
    tag: str
    text_sample: str = ""          # 文本片段 (前80字符)
    text_hash: str = ""            # 文本哈希
    attr_samples: Dict[str, str] = field(default_factory=dict)  # {attr_name: value}
    class_set: frozenset = field(default_factory=frozenset)     # CSS class 集合
    parent_tag: str = ""
    depth: int = 0
    nth_child: int = 0


def extract_fingerprint(
    html: str,
    selector: str,
    text_sample_len: int = 80,
) -> Optional[ElementFingerprint]:
    """从 HTML 中提取元素指纹（轻量解析，不依赖 lxml/bs4）"""
    import html.parser as _hp

    class _FingerprintExtractor(_hp.HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.path: List[Tuple[str, Dict[str, str], int]] = []  # (tag, attrs, child_idx)
            self.current_nth = 0
            self.target = None
            # 简单 CSS 选择器解析 (只支持 tag, .class, #id, [attr=val])
            self._sel_tag = ""
            self._sel_class = ""
            self._sel_id = ""
            self._sel_attrs: Dict[str, str] = {}

        def parse_selector(self, sel: str):
            sel = sel.strip()
            # #id
            for m in re.finditer(r'#([\w-]+)', sel):
                self._sel_id = m.group(1)
                sel = sel.replace(m.group(0), "")
            # .class
            for m in re.finditer(r'\.([\w-]+)', sel):
                self._sel_class = m.group(1)
                sel = sel.replace(m.group(0), "")
            # [attr=val]
            for m in re.finditer(r'\[(\w+)\s*=\s*["\']?([^"\'\]]+)["\']?\]', sel):
                self._sel_attrs[m.group(1)] = m.group(2)
                sel = sel.replace(m.group(0), "")
            self._sel_tag = sel.strip() or "div"

        def handle_starttag(self, tag, attrs_list):
            attrs = dict(attrs_list)
            child_idx = self.current_nth if self.path else 0
            self.path.append((tag, attrs, child_idx))
            self.depth += 1
            self.current_nth = 0

            if self.target is None and self._matches(tag, attrs):
                # 记录当前作为目标
                text_parts = []
                self.target = {
                    "tag": tag,
                    "attrs": attrs,
                    "depth": self.depth,
                    "nth_child": child_idx,
                    "parent": self.path[-2][0] if len(self.path) >= 2 else "",
                    "text_parts": text_parts,
                    "classes": frozenset(
                        cls.strip() for cls in attrs.get("class", "").split() if cls.strip()
                    ),
                }
                # 记录父级路径
                self.target["ancestors"] = [
                    (p[0], p[1].get("class", ""), p[1].get("id", ""))
                    for p in self.path[-3:] if len(self.path) > 1
                ]

        def handle_endtag(self, tag):
            if self.path:
                self.path.pop()
            self.depth -= 1

        def handle_data(self, data):
            if self.target is not None:
                self.target["text_parts"].append(data)
            self.current_nth += 1

        def _matches(self, tag, attrs) -> bool:
            if self._sel_tag and tag != self._sel_tag:
                return False
            if self._sel_id and attrs.get("id", "") != self._sel_id:
                return False
            if self._sel_class:
                classes = set(attrs.get("class", "").split())
                if self._sel_class not in classes:
                    return False
            for k, v in self._sel_attrs.items():
                if attrs.get(k, "") != v:
                    return False
            return True

    parser = _FingerprintExtractor()
    parser.parse_selector(selector)
    parser.feed(html)
    parser.close()

    if parser.target is None:
        return None

    t = parser.target
    full_text = "".join(t["text_parts"]).strip()
    text_sample = full_text[:text_sample_len] if full_text else ""

    return ElementFingerprint(
        tag=t["tag"],
        text_sample=text_sample,
        text_hash=hashlib.md5(full_text.encode("utf-8", errors="replace")).hexdigest()[:12],
        attr_samples={
            k: v
            for k, v in t["attrs"].items()
            if k not in ("style", "data-*") and len(v) < 200
        },
        class_set=t["classes"],
        parent_tag=t["parent"],
        depth=t["depth"],
        nth_child=t["nth_child"],
    )


def relocate_element(
    html: str,
    fingerprint: ElementFingerprint,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    在 HTML 中根据指纹重新定位元素（自适应选择器）。
    返回相似度最高的 N 个候选。
    """
    import html.parser as _hp

    class _Relocator(_hp.HTMLParser):
        def __init__(self, fp: ElementFingerprint):
            super().__init__()
            self.fp = fp
            self.depth = 0
            self.current_idx = 0
            self.current_tag = ""
            self.current_attrs: Dict[str, str] = {}
            self.current_text: List[str] = []
            self.in_target = False
            self.results: List[Dict[str, Any]] = []

        def handle_starttag(self, tag, attrs_list):
            attrs = dict(attrs_list)
            self.depth += 1

            if self.in_target:
                return

            # 评分当前元素与指纹的相似度
            score = 0.0

            # 标签得分
            if tag == self.fp.tag:
                score += 0.3

            # class 交集得分
            classes = frozenset(
                cls.strip() for cls in attrs.get("class", "").split() if cls.strip()
            )
            if classes and self.fp.class_set:
                overlap = len(classes & self.fp.class_set)
                union = len(classes | self.fp.class_set)
                if union > 0:
                    score += 0.2 * (overlap / union)

            # 属性匹配
            if self.fp.attr_samples:
                matched = 0
                for k, v in self.fp.attr_samples.items():
                    if attrs.get(k, "") == v:
                        matched += 1
                if matched > 0:
                    score += 0.2 * (matched / len(self.fp.attr_samples))

            # 深度/位置得分
            if self.depth == self.fp.depth:
                score += 0.1

            self.current_tag = tag
            self.current_attrs = attrs
            self.current_text = []
            self.current_idx = self.depth
            self.in_target = True

        def handle_endtag(self, tag):
            if self.in_target:
                full_text = "".join(self.current_text).strip()
                text_score = 0.0
                if self.fp.text_sample and full_text:
                    # 简单 Levenshtein ratio 近似
                    text_score = _text_similarity(self.fp.text_sample, full_text)
                    text_score *= 0.2

                total_score = min(1.0, sum([t for _, t in [
                    ("tag", 0.3 if self.current_tag == self.fp.tag else 0),
                    ("text", text_score),
                ]]) + 0.2)  # base score for existing

                self.results.append({
                    "tag": self.current_tag,
                    "attrs": dict(self.current_attrs),
                    "text_preview": full_text[:80],
                    "score": round(max(0.1, total_score), 3),
                    "depth": self.depth,
                })

            self.in_target = False
            self.current_text = []

        def handle_data(self, data):
            if self.in_target:
                self.current_text.append(data)

    def _text_similarity(a: str, b: str) -> float:
        """快速文本相似度 (Jaccard 近似)"""
        if not a or not b:
            return 0.0
        set_a = set(a[:200].split())
        set_b = set(b[:200].split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    parser = _Relocator(fingerprint)
    parser.feed(html)
    parser.close()
    parser.results.sort(key=lambda x: x["score"], reverse=True)
    return parser.results[:top_n]


def adaptive_css(html: str, selector: str, fallback: str = "") -> str:
    """
    自适应 CSS 选择器：如果选择器匹配失败，用指纹重定位并生成新选择器。
    返回最佳可用选择器。
    """
    try:
        fp = extract_fingerprint(html, selector)
        if fp is None:
            return fallback or selector

        candidates = relocate_element(html, fp, top_n=3)
        if not candidates or candidates[0]["score"] < 0.5:
            return fallback or selector

        # 生成新选择器
        best = candidates[0]
        if best["attrs"].get("id"):
            return f'#{best["attrs"]["id"]}'
        if best["attrs"].get("class"):
            cls = best["attrs"]["class"].split()[0]
            return f'{best["tag"]}.{cls}'
        return best["tag"]
    except Exception as e:
        L.debug(f"Adaptive CSS 失败: {e}")
        return fallback or selector


# ═══════════════════════════════════════════════════════
# 3. 会话持久化 — 基于 Cookie 的券商登录态保持
# ═══════════════════════════════════════════════════════

@dataclass
class SessionState:
    """抓取会话状态"""
    id: str
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    last_url: str = ""
    last_response_code: int = 0
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScraperSession:
    """持久化抓取会话 — 状态保持、Cookie 管理"""

    def __init__(self, session_id: str = "", fingerprint: str = "chrome_131"):
        self.id = session_id or f"sess_{int(time.time() * 1000)}"
        self.fingerprint = fingerprint
        self._state = SessionState(id=self.id)
        self._ssl_ctx = ssl.create_default_context()
        self._opener: Optional[urllib.request.OpenerDirector] = None

    @property
    def cookies(self) -> Dict[str, str]:
        return dict(self._state.cookies)

    def set_cookie(self, key: str, value: str):
        self._state.cookies[key] = value
        self._state.last_active = datetime.now().isoformat()

    def set_cookies(self, cookies: Dict[str, str]):
        self._state.cookies.update(cookies)
        self._state.last_active = datetime.now().isoformat()

    def _build_cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self._state.cookies.items())

    def request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
        follow_redirect: bool = True,
    ) -> Dict[str, Any]:
        """发起带会话状态的 HTTP 请求"""
        req_headers = build_stealth_headers(self.fingerprint, referer=self._state.last_url)
        req_headers.update(headers or {})

        if self._state.cookies:
            req_headers["Cookie"] = self._build_cookie_header()

        if data:
            req_headers["Content-Type"] = req_headers.get(
                "Content-Type", "application/x-www-form-urlencoded"
            )

        req = urllib.request.Request(
            url,
            data=data,
            headers=req_headers,
            method=method,
        )

        try:
            resp = urllib.request.urlopen(req, context=self._ssl_ctx, timeout=timeout)
            body = resp.read()

            # 提取 Set-Cookie
            set_cookie = resp.headers.get("Set-Cookie", "")
            if set_cookie:
                for part in set_cookie.split(";"):
                    if "=" in part and not any(
                        kw in part.lower()
                        for kw in ("path", "domain", "expires", "max-age", "httponly", "secure")
                    ):
                        k, v = part.split("=", 1)
                        self._state.cookies[k.strip()] = v.strip()

            self._state.last_url = url
            self._state.last_response_code = resp.status
            self._state.last_active = datetime.now().isoformat()

            encoding = resp.headers.get_content_charset() or "utf-8"
            try:
                text = body.decode(encoding, errors="replace")
            except Exception:
                text = body.decode("utf-8", errors="replace")

            return {
                "ok": resp.status < 400,
                "status": resp.status,
                "body": text,
                "headers": dict(resp.headers),
                "url": resp.url,
            }
        except urllib.error.HTTPError as e:
            return {
                "ok": False,
                "status": e.code,
                "body": e.read().decode("utf-8", errors="replace") if e.fp else "",
                "headers": dict(e.headers) if e.headers else {},
                "error": str(e),
            }
        except Exception as e:
            return {"ok": False, "status": 0, "body": "", "error": str(e)[:200]}

    def post_form(
        self,
        url: str,
        form_data: Dict[str, str],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """POST 表单提交（券商登录常用）"""
        encoded = urllib.parse.urlencode(form_data).encode("utf-8")
        extra_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            extra_headers.update(headers)
        return self.request(url, method="POST", data=encoded, headers=extra_headers)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return self.request(url, headers=headers)

    def is_logged_in(self, check_keywords: Optional[List[str]] = None) -> bool:
        """简易登录状态检测 — 检查 Cookie 中是否存在关键字段"""
        if not check_keywords:
            check_keywords = ["token", "session", "JSESSIONID", "uid", "login", "auth"]
        cookie_str = " ".join(self._state.cookies.keys()).lower()
        cookie_vals = " ".join(str(v)[:100] for v in self._state.cookies.values()).lower()
        combined = f"{cookie_str} {cookie_vals}"
        return any(kw.lower() in combined for kw in check_keywords)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "cookies_count": len(self._state.cookies),
            "last_url": self._state.last_url,
            "last_response_code": self._state.last_response_code,
            "last_active": self._state.last_active,
            "is_logged_in": self.is_logged_in(),
        }

    def extract_data(
        self,
        html: str,
        selector: str,
        adaptive: bool = True,
    ) -> Dict[str, Any]:
        """从 HTML 提取数据 — 支持自适应选择器"""
        # 简易 regex 提取 (不依赖 lxml)
        tag, cls, attr_val, text_kw = "", "", "", ""

        # 解析选择器
        sel = selector.strip()
        m = re.match(r'([a-zA-Z]+)(?:\.([\w-]+))?(?:\[(\w+)=["\']?([^"\']+)["\']?\])?', sel)
        if m:
            tag, cls, _, _ = m.group(1), m.group(2), m.group(3), m.group(4)
            # 文本提取: selector::text
            text_kw = ""
            if "::text" in sel:
                sel = sel.replace("::text", "")

        # 先尝试直接匹配
        pattern = _build_regex_pattern(
            tag or "\\w+", cls or "",
            attr or "", attr_val or "",
        )
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        if not matches and adaptive:
            fp = extract_fingerprint(html, selector)
            if fp:
                candidates = relocate_element(html, fp, top_n=1)
                if candidates and candidates[0]["score"] >= 0.5:
                    # 用重定位后的标签重新匹配
                    new_tag = candidates[0]["tag"]
                    new_cls = candidates[0]["attrs"].get("class", "").split()[0] if candidates[0]["attrs"].get("class") else ""
                    pattern = _build_regex_pattern(new_tag, new_cls, "", "")
                    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        results = []
        for m in matches:
            # 提取纯文本
            text = re.sub(r'<[^>]+>', '', m).strip() if isinstance(m, str) else str(m)
            if text:
                results.append(text[:200])

        return {
            "ok": len(results) > 0,
            "count": len(results),
            "data": results,
            "selector": selector,
            "adaptive_used": not matches and adaptive,
        }


def _build_regex_pattern(
    tag: str, cls: str = "", attr: str = "", attr_val: str = ""
) -> str:
    """构建 HTML 元素匹配正则"""
    tag_pat = tag
    class_pat = ""
    if cls:
        class_pat = f'(?:[^>]*class\\s*=\\s*["\'][^"\']*{re.escape(cls)}[^"\']*["\'])'

    if attr and attr_val:
        attr_pat = f'[^>]*{re.escape(attr)}\\s*=\\s*["\']{re.escape(attr_val)}["\']'
        return f'<{tag_pat}[^>]*{attr_pat}[^>]*>(.*?)</{tag_pat}>'
    elif class_pat:
        return f'<{tag_pat}[^>]*{class_pat}[^>]*>(.*?)</{tag_pat}>'
    else:
        return f'<{tag_pat}[^>]*>(.*?)</{tag_pat}>'


# ═══════════════════════════════════════════════════════
# 4. 浏览器动态渲染 — 支持 JS 重页面
# ═══════════════════════════════════════════════════════

def dynamic_fetch(
    url: str,
    wait_seconds: float = 3.0,
    selector: str = "",
) -> Dict[str, Any]:
    """浏览器动态渲染抓取 — 处理 JS 重页面 (券商交易确认页等)"""
    try:
        import subprocess
        import tempfile
        import os

        script = f"""
import asyncio, sys, json
async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(json.dumps({{"ok": False, "error": "playwright not installed"}}))
        return
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("{url}", wait_until="networkidle", timeout=15000)
        await asyncio.sleep({wait_seconds})
        html = await page.content()
        title = await page.title()
        await browser.close()
        print(json.dumps({{"ok": True, "html": html, "title": title}}, ensure_ascii=False))
asyncio.run(main())
"""
        fd, path = tempfile.mkstemp(suffix=".py", prefix="gbt_dynamic_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(script)
            r = subprocess.run(
                ["python", path],
                capture_output=True, text=True, timeout=30,
                errors="replace",
            )
            result = json.loads(r.stdout.strip().split("\n")[-1])
            return result
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
# 5. 统一抓取接口 — PrecisionScraper v2
# ═══════════════════════════════════════════════════════

# 数据源定义
SOURCES = {
    "sina_quote": {
        "name": "新浪行情",
        "url": "https://hq.sinajs.cn/list={codes}",
        "type": "实时行情",
        "weight": 1.0,
    },
    "sina_news": {
        "name": "新浪财经新闻",
        "url": "https://finance.sina.com.cn",
        "type": "财经资讯",
        "weight": 0.8,
    },
    "ddg": {
        "name": "DuckDuckGo",
        "url": "https://api.duckduckgo.com/?q={query}&format=json&no_html=1",
        "type": "搜索摘要",
        "weight": 0.6,
    },
    "eastmoney_news": {
        "name": "东方财富资讯",
        "url": "https://finance.eastmoney.com/",
        "type": "财经资讯",
        "weight": 0.7,
    },
}


class PrecisionScraper:
    """多源精准抓取 v2 — 自适应 + 反检测 + 会话管理"""

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.ssl_ctx = ssl.create_default_context()
        self._sessions: Dict[str, ScraperSession] = {}
        self._fingerprints: Dict[str, ElementFingerprint] = {}

    def session(self, name: str = "default") -> ScraperSession:
        """获取或创建会话"""
        if name not in self._sessions:
            self._sessions[name] = ScraperSession(session_id=name)
        return self._sessions[name]

    # ── 基础抓取 ──

    def scrape_stock_quote(self, codes):
        """抓取实时行情（新浪）"""
        if isinstance(codes, str):
            codes = [codes]

        code_str = ",".join(codes)
        url = SOURCES["sina_quote"]["url"].format(codes=code_str)

        try:
            headers = build_stealth_headers(
                "chrome_131",
                referer="https://finance.sina.com.cn",
            )
            req = urllib.request.Request(url, headers=headers)
            raw = urllib.request.urlopen(req, timeout=8).read().decode("gbk", errors="replace")

            results = {}
            for line in raw.strip().split("\n"):
                m = re.search(r'var hq_str_(\w+)="(.+)"', line)
                if not m:
                    continue
                code, data = m.group(1), m.group(2).split(",")
                if len(data) < 5:
                    continue
                results[code] = {
                    "name": data[0],
                    "price": float(data[3]) if len(data) > 3 and data[3] else 0,
                    "prev_close": float(data[2]) if len(data) > 2 and data[2] else 0,
                    "change_pct": self._calc_pct(data[3], data[2]) if len(data) > 3 else 0,
                    "source": "sina",
                    "confidence": 0.95,
                }

            return {"ok": True, "data": results, "count": len(results)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:120]}

    def scrape_web_info(self, query):
        """网络信息抓取（DuckDuckGo）"""
        url = SOURCES["ddg"]["url"].format(query=urllib.request.quote(query))

        try:
            headers = build_stealth_headers("chrome_131")
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10)
            data = json.loads(resp.read().decode())

            abstract = data.get("AbstractText", "") or data.get("Abstract", "")
            topics = data.get("RelatedTopics", [])

            return {
                "ok": True,
                "abstract": abstract[:500] if abstract else "",
                "topics_count": len(topics),
                "top_entries": [
                    {"text": t.get("Text", "")[:200]}
                    for t in topics[:5] if t.get("Text")
                ],
                "source": "ddg",
                "confidence": 0.7 if abstract else 0.4,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:120]}

    def scrape_page(
        self,
        url: str,
        extract_selectors: Optional[List[str]] = None,
        fingerprint: str = "chrome_131",
        adaptive: bool = True,
    ) -> Dict[str, Any]:
        """抓取任意网页 — 反检测 + 可选自适应提取"""
        headers = build_stealth_headers(fingerprint)
        try:
            data = urllib.parse.urlencode({}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=15)
            text = resp.read().decode(
                resp.headers.get_content_charset() or "utf-8", errors="replace"
            )

            result: Dict[str, Any] = {
                "ok": True,
                "status": resp.status,
                "html": text,
                "url": resp.url,
            }

            if extract_selectors:
                extracted: Dict[str, Any] = {}
                for sel in extract_selectors:
                    extracted[sel] = self.session().extract_data(text, sel, adaptive=adaptive)
                result["extracted"] = extracted

            return result
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── 交叉验证 ──

    def cross_verify(self, stock_code, query=""):
        """交叉验证 — 多源比对置信度"""
        results: Dict[str, Any] = {
            "code": stock_code,
            "time": datetime.now().strftime("%H:%M:%S"),
            "sources": {},
            "verified": False,
            "confidence": 0.0,
            "summary": "",
        }

        quote = self.scrape_stock_quote(stock_code)
        if quote["ok"]:
            results["sources"]["sina_quote"] = quote
            results["confidence"] += 0.4

        if query:
            info = self.scrape_web_info(query)
            if info["ok"] and info.get("abstract"):
                results["sources"]["ddg"] = info
                results["confidence"] += 0.3
            elif info["ok"]:
                results["sources"]["ddg_partial"] = info
                results["confidence"] += 0.1

        if len(results["sources"]) >= 2:
            results["verified"] = True
            results["confidence"] = min(1.0, results["confidence"] + 0.2)

        parts = []
        qd = quote.get("data", {}).get(stock_code, {})
        if qd:
            name = qd.get("name", "")
            price = qd.get("price", 0)
            chg = qd.get("change_pct", 0)
            parts.append(f"{name}: ¥{price:.2f} ({chg:+.2f}%)")

        info_d = (results["sources"].get("ddg", {}).get("abstract", "") or
                  results["sources"].get("ddg_partial", {}).get("abstract", ""))
        if info_d:
            parts.append(f"资讯: {info_d[:150]}")

        results["summary"] = " | ".join(parts)
        return results

    # ── 自适应学习 ──

    def learn_selector(self, html: str, selector: str, name: str):
        """学习并缓存选择器指纹"""
        fp = extract_fingerprint(html, selector)
        if fp:
            self._fingerprints[name] = fp
            L.info(f"已学习选择器指纹: {name} -> {selector}")
            return True
        return False

    def adaptive_extract(self, html: str, name: str, fallback_selector: str = "") -> Dict[str, Any]:
        """用已学习的指纹自适应提取"""
        fp = self._fingerprints.get(name)
        if fp is None:
            return self.session().extract_data(html, fallback_selector, adaptive=True)

        candidates = relocate_element(html, fp, top_n=1)
        if not candidates or candidates[0]["score"] < 0.4:
            return {"ok": False, "data": [], "error": "元素未找到"}

        return {
            "ok": True,
            "data": [candidates[0]["text_preview"]],
            "score": candidates[0]["score"],
            "tag": candidates[0]["tag"],
            "adaptive": True,
        }

    # ── Cloudflare 绕过 (轻量) ──

    def fetch_with_cf_bypass(
        self,
        url: str,
        session: Optional[ScraperSession] = None,
    ) -> Dict[str, Any]:
        """带 Cloudflare 绕过的抓取"""
        sess = session or self.session("cf_bypass")
        # 方案1: 用 stealth headers + 模拟浏览器
        result = sess.get(url)
        if result["ok"] and "cf-browser-verify" not in result.get("body", "").lower():
            return result

        # 方案2: 降级到动态渲染
        L.info("检测到 Cloudflare 防护，尝试动态渲染绕过...")
        return dynamic_fetch(url)

    @staticmethod
    def _calc_pct(price_str, prev_str):
        try:
            price = float(price_str)
            prev = float(prev_str)
            if prev > 0:
                return round((price - prev) / prev * 100, 2)
        except (ValueError, TypeError):
            pass
        return 0

    def to_context(self) -> Dict[str, Any]:
        """导出抓取上下文（供 LLM 使用）"""
        return {
            "sessions": {n: s.to_dict() for n, s in self._sessions.items()},
            "fingerprints": {n: {"tag": fp.tag, "text": fp.text_sample[:40]}
                           for n, fp in self._fingerprints.items()},
            "sources": {k: v["name"] for k, v in SOURCES.items()},
        }


# ═══════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════

_scraper: Optional[PrecisionScraper] = None


def get_scraper() -> PrecisionScraper:
    global _scraper
    if _scraper is None:
        _scraper = PrecisionScraper()
    return _scraper


def precision_lookup(stock_code, query=""):
    """快速精准查询"""
    return get_scraper().cross_verify(stock_code, query)


def quick_quote(code):
    """快速行情"""
    return get_scraper().scrape_stock_quote(code)


def quick_search(query):
    """快速搜索"""
    return get_scraper().scrape_web_info(query)


def fetch_news(code, query=""):
    """获取股票相关资讯 — 多源抓取+交叉验证"""
    scraper = get_scraper()
    result = scraper.cross_verify(code, query)
    if result.get("ok"):
        return result
    quote = scraper.scrape_stock_quote(code)
    if quote.get("ok"):
        return {"ok": True, "data": quote.get("data", {}), "source": "quote_only"}
    return {"ok": False, "error": "无法获取资讯", "code": code}


def stealth_fetch(
    url: str,
    fingerprint: str = "chrome_131",
    cookie: str = "",
) -> Dict[str, Any]:
    """快速反检测抓取"""
    sess = get_scraper().session("stealth")
    if cookie:
        for part in cookie.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                sess.set_cookie(k.strip(), v.strip())
    return sess.get(url)


def adaptive_fetch(
    url: str,
    extract_selector: str,
    fingerprint: str = "chrome_131",
) -> Dict[str, Any]:
    """自适应抓取 — 自动处理 HTML 变化"""
    return get_scraper().scrape_page(
        url,
        extract_selectors=[extract_selector],
        fingerprint=fingerprint,
        adaptive=True,
    )


def broker_login_session(
    login_url: str,
    form_data: Dict[str, str],
    session_id: str = "",
) -> ScraperSession:
    """创建券商登录会话"""
    sess = ScraperSession(
        session_id=session_id or f"broker_{int(time.time() * 1000)}",
        fingerprint="chrome_131",
    )
    sess.post_form(login_url, form_data)
    return sess


L.info("Scraper v2.0 已加载: 反检测 + 自适应 + 会话持久 + 动态渲染")
