"""market.py - A-Shares Market connector (东方财富实时数据 + 新浪备用)
- 主源：东方财富 push2.eastmoney.com
- 备用源：新浪 hq.sinajs.cn（数据稍延迟但稳定）
- 错误脱敏：不透传上游 urllib HTTPError 字符串，改成友好文案
- 严禁任何 fake / mock 行情数据（用户铁律）
"""
import urllib.request, json, re, time, logging

_LOG = logging.getLogger("gbt.connectors.market")


def _friendly_error(e: Exception) -> str:
    """将 urllib / 网络异常脱敏为友好文案（避免透传'HTTP Error 502: Bad Gateway'误导用户）"""
    msg = str(e) or ""
    if "HTTP Error" in msg:
        # 上游 502/503/504 一律转成"数据源暂时不可达"
        return "上游数据源暂时不可达，请稍后重试或切换备用源"
    if "timed out" in msg.lower():
        return "上游数据源响应超时"
    if "Connection" in msg or "RemoteDisconnected" in msg:
        return "上游数据源连接中断"
    return f"行情获取失败：{msg[:120]}"


def _http_get(url: str, timeout: int = 8, headers: dict = None):
    """统一的 http GET，自动设置 User-Agent"""
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return urllib.request.urlopen(req, timeout=timeout)

def get_indices():
    try:
        codes = ["1.000001","0.399001","0.399006","1.000688","1.000300"]
        secids = ",".join(codes)
        url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f3,f4,f12,f14&secids={secids}"
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())
        indices = []
        for item in data.get("data", {}).get("diff", []):
            # EastMoney index quote fields are scaled by 100.
            indices.append({
                "code": item.get("f12", ""),
                "name": item.get("f14", ""),
                "price": round((item.get("f2", 0) or 0) / 100.0, 2),
                "change": round((item.get("f4", 0) or 0) / 100.0, 2),
                "pct": round((item.get("f3", 0) or 0) / 100.0, 2),
            })
        if indices: return {"ok": True, "indices": indices}
    except Exception: pass
    try:
        sina_codes = ["sh000001","sz399001","sz399006","sh000688"]
        sina_names = ["上证指数","深证成指","创业板指","科创50"]
        url = "https://hq.sinajs.cn/list=" + ",".join(sina_codes)
        req = urllib.request.Request(url, headers={"Referer":"https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read().decode("gbk")
        indices = []
        lines = raw.strip().split(chr(10))
        for i, line in enumerate(lines):
            q = line.find(chr(34))
            q2 = line.find(chr(34), q+1)
            if q >= 0 and q2 > q:
                inner = line[q+1:q2]
                parts = inner.split(",")
                # T-009 修复：Sina 真实字段映射 = [name, current, prev_close, open, high, low, ...]
                # 旧代码把 prev_close 当 change / open 当 pct 是错的 → 上证指数曾显示 pct=4073%
                if len(parts) >= 6:
                    _price = float(parts[1])
                    _prev_close = float(parts[2])
                    _change = round(_price - _prev_close, 2)
                    _pct = round((_change / _prev_close * 100.0), 2) if _prev_close else 0.0
                    indices.append({
                        "code": sina_codes[i],
                        "name": sina_names[i],
                        "price": _price,
                        "change": _change,
                        "pct": _pct,
                    })
        if indices: return {"ok": True, "indices": indices}
    except Exception as e: return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "No market data"}

def _get_stock_sina(code: str) -> dict:
    """新浪备用源 — 稳定但只有实时价/昨收/开/高/低/成交量，无市值/PB/PE"""
    try:
        if code.startswith(("6", "5", "9")):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"
        url = f"https://hq.sinajs.cn/list={symbol}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        req.add_header("Referer", "https://finance.sina.com.cn")
        with _http_get(url, timeout=8, headers={"Referer": "https://finance.sina.com.cn"}) as r:
            raw = r.read().decode("gbk", errors="ignore")
        # 解析 var hq_str_shXXXXXX="name,open,prev_close,price,high,low,...";
        m = re.search(r'"([^"]+)"', raw)
        if not m:
            return {"ok": False, "error": "新浪备用源返回格式异常"}
        parts = m.group(1).split(",")
        if len(parts) < 6:
            return {"ok": False, "error": "新浪备用源字段不足"}
        _name = parts[0]
        _open = float(parts[1] or 0)
        _prev_close = float(parts[2] or 0)
        _price = float(parts[3] or 0)
        _high = float(parts[4] or 0)
        _low = float(parts[5] or 0)
        # Sina 字段顺序：[name, open, prev_close, price, high, low, ...]
        # 注意：与东方财富不同！Sina 第 3 位是昨收，第 4 位是当前价
        _change = round(_price - _prev_close, 2)
        _pct = round((_change / _prev_close * 100.0), 2) if _prev_close else 0.0
        _date = parts[30] if len(parts) > 30 else ""
        _time = parts[31] if len(parts) > 31 else ""
        _volume = float(parts[5] or 0) if False else float(parts[8] or 0)  # parts[8] 成交量(股)
        return {
            "ok": True,
            "source": "sina",
            "code": code,
            "name": _name,
            "price": _price,
            "change": _change,
            "pct": _pct,
            "open": _open,
            "high": _high,
            "low": _low,
            "prev_close": _prev_close,
            "volume": _volume,
            "amount": 0.0,
            "amplitude": 0.0,
            "market_cap": 0.0,
            "float_cap": 0.0,
            "updated": f"{_date} {_time}".strip() or time.strftime("%H:%M:%S"),
        }
    except Exception as e:
        return {"ok": False, "error": _friendly_error(e)}


def get_stock(code):
    """个股实时行情 — 主源东方财富 + 备用源新浪
    严禁任何 fake / mock 数据（用户铁律）：失败就老实返回错误，不兜底假数据
    """
    # 主源：东方财富
    try:
        prefix = "1" if code.startswith(("6", "68")) else "0"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f170&secid={prefix}.{code}"
        with _http_get(url, timeout=8) as r:
            data = json.loads(r.read()).get("data", {})
        if not data:
            raise ValueError("东方财富返回 data 为空")
        price = round((data.get("f43", 0) or 0) / 100.0, 2)
        if price <= 0:
            raise ValueError("东方财富返回价格无效")
        high = round((data.get("f44", 0) or 0) / 100.0, 2)
        low = round((data.get("f45", 0) or 0) / 100.0, 2)
        open_price = round((data.get("f46", 0) or 0) / 100.0, 2)
        volume = int(data.get("f47", 0) or 0)
        amount = round((data.get("f48", 0) or 0) / 100000000.0, 2)
        amplitude = round((data.get("f50", 0) or 0) / 100.0, 2)
        prev_close = round((data.get("f60", 0) or 0) / 100.0, 2)
        market_cap = round((data.get("f116", 0) or 0) / 100000000.0, 2)
        float_cap = round((data.get("f117", 0) or 0) / 100000000.0, 2)
        pct = round((data.get("f170", 0) or 0) / 100.0, 2)
        change = round(price - prev_close, 2) if prev_close else 0
        return {
            "ok": True,
            "source": "eastmoney",
            "code": code,
            "name": data.get("f58", ""),
            "price": price,
            "change": change,
            "pct": pct,
            "open": open_price,
            "high": high,
            "low": low,
            "prev_close": prev_close,
            "volume": volume,
            "amount": amount,
            "amplitude": amplitude,
            "market_cap": market_cap,
            "float_cap": float_cap,
            "updated": time.strftime("%H:%M:%S"),
        }
    except Exception as e:
        _LOG.warning("eastmoney get_stock(%s) failed: %s — falling back to sina", code, e)
        # 降级到新浪
        sina_result = _get_stock_sina(code)
        if sina_result.get("ok"):
            return sina_result
        # 双源都失败：返回脱敏后的错误（严禁 fake 数据）
        return {"ok": False, "error": _friendly_error(e), "sina_error": sina_result.get("error", "")}

def market_handle(action, **params):
    h = {"get_indices": get_indices, "get_stock": lambda: get_stock(params.get("code",""))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
