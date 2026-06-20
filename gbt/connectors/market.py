"""market.py — A-Shares Market connector (东方财富实时数据)"""
import urllib.request, json, re

def get_indices():
    try:
        codes = ["1.000001","0.399001","0.399006","1.000688","1.000300"]
        secids = ",".join(codes)
        url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f3,f4,f12,f14&secids={secids}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        indices = []
        for item in data.get("data", {}).get("diff", []):
            indices.append({"code": item.get("f12",""), "name": item.get("f14",""),
                           "price": item.get("f2",0), "change_pct": item.get("f3",0)})
        return {"ok": True, "indices": indices}
    except Exception as e: return {"ok": False, "error": str(e)}

def get_stock(code):
    try:
        prefix = "1" if code.startswith(("6","68")) else "0"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f170&secid={prefix}.{code}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read()).get("data", {})
        return {"ok": True, "code": code, "name": data.get("f58",""), "price": data.get("f43",0),
                "change": data.get("f170",0), "change_pct": data.get("f170",0), "volume": data.get("f47",0)}
    except Exception as e: return {"ok": False, "error": str(e)}

def market_handle(action, **params):
    h = {"get_indices": get_indices, "get_stock": lambda: get_stock(params.get("code",""))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
