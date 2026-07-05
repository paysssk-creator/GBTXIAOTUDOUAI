"""market.py - A-Shares Market connector (东方财富实时数据 + 新浪备用)"""
import urllib.request, json, re

def get_indices():
    try:
        codes = ["1.000001","0.399001","0.399006","1.000688","1.000300"]
        secids = ",".join(codes)
        url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f3,f4,f12,f14&secids={secids}"
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())
        indices = []
        for item in data.get("data", {}).get("diff", []):
            indices.append({"code": item.get("f12",""), "name": item.get("f14",""),
                           "price": item.get("f2",0), "change": item.get("f4",0),
                           "pct": item.get("f3",0)})
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
                if len(parts) >= 5:
                    indices.append({"code": sina_codes[i], "name": sina_names[i],
                                   "price": float(parts[1]), "change": float(parts[2]),
                                   "pct": float(parts[3])})
        if indices: return {"ok": True, "indices": indices}
    except Exception: pass
    return {"ok": False, "error": "No market data"}

def get_stock(code):
    # 东方财富
    try:
        prefix = "1" if code.startswith(("6","68")) else "0"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f170&secid={prefix}.{code}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read()).get("data", {})
        price = (data.get("f43") or 0) / 100
        prev = (data.get("f60") or 0) / 100
        change = (data.get("f170") or 0) / 100
        return {"ok": True, "code": code, "name": data.get("f58",""),
                "price": price, "prev_close": prev, "change": change,
                "high": (data.get("f44") or 0)/100, "low": (data.get("f45") or 0)/100,
                "open": (data.get("f46") or 0)/100, "volume": data.get("f47",0)}
    except Exception:
        pass
    # 新浪备用
    try:
        prefix = "sh" if code.startswith(("6","68")) else "sz"
        url = f"https://hq.sinajs.cn/list={prefix}{code}"
        req = urllib.request.Request(url, headers={"Referer":"https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read().decode("gbk")
        inner = raw.split('"')[1] if '"' in raw else ""
        parts = inner.split(",")
        return {"ok": True, "code": code, "name": parts[0],
                "price": float(parts[3]), "prev_close": float(parts[2]),
                "change": float(parts[3])-float(parts[2]),
                "open": float(parts[1]), "high": float(parts[4]), "low": float(parts[5])}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def market_handle(action, **params):
    h = {"get_indices": get_indices, "get_stock": lambda: get_stock(params.get("code",""))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
