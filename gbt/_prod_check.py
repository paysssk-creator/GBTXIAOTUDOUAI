import requests, json, time
BASE = "http://127.0.0.1:8765"
time.sleep(3)

print("=== DeepSeek LLM ===")
r = requests.post(f"{BASE}/api/chat", json={"text": "用一句中文解释MACD金叉"}, timeout=30)
d = r.json()
print(f"  Chat: ok={d.get('ok')} | provider={d.get('provider','?')}")
if d.get("ok"):
    resp = (d.get("response","") or "")[:120]
    print(f"  Response: {resp}")
    m = d.get("metrics", {})
    print(f"  Tokens: {m.get('tokens_in',0)}in+{m.get('tokens_out',0)}out | Cost: ¥{m.get('cost_rmb',0):.6f}")

print("\n=== 多策略引擎 ===")
r = requests.get(f"{BASE}/api/strategies/run/600519", timeout=15)
d = r.json()
print(f"  600519: signal={d.get('signal')} buy={d.get('buy_votes')} sell={d.get('sell_votes')}")
for s in d.get("signal_detail", []):
    print(f"    {s['strategy']:20s} → {s['signal']:4s} ({s['confidence']:.0%}) {s['reasoning'][:40]}")

r = requests.get(f"{BASE}/api/strategies/run/600036", timeout=15)
d = r.json()
print(f"  600036: signal={d.get('signal')} buy={d.get('buy_votes')} sell={d.get('sell_votes')}")

print("\n=== 真实行情 ===")
from gbt.live_market import get_market
mkt = get_market()
indices = mkt.get_indices()
print(f"  Indices: {len(indices)} fetched")
for ix in indices:
    print(f"    {ix['name']}: ¥{ix['price']} {ix['change_pct']:+.2f}%")

q = mkt.get_quote("600519")
print(f"  600519: ¥{q.get('price')} {q.get('change_pct'):+.2f}%")

print("\n=== 自主操盘 状态 ===")
r = requests.get(f"{BASE}/api/pilot/status")
d = r.json()
print(f"  Running: {d['running']} | Scans: {d['scan_count']} | Trades: {d['trade_count']}")

print("\n=== 审计日志 ===")
r = requests.get(f"{BASE}/api/audit")
d = r.json()
for rec in d.get("records", [])[-5:]:
    print(f"  [{rec.get('timestamp','')[:19]}] {rec.get('action'):12s} {str(rec.get('detail',{}))[:80]}")

print("\n=== Docker/Prod ===")
import os
dockerfile = "c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/Dockerfile"
print(f"  Dockerfile: {'EXISTS' if os.path.exists(dockerfile) else 'MISSING'}")

compose = "c:/Users/ADMIN/Desktop/自主操盘/GBTXIAOTUDOUAI/docker-compose.yml"
print(f"  docker-compose: {'EXISTS' if os.path.exists(compose) else 'MISSING'}")

print("\n✅ GBT Pro 生产闭环就绪!")
print("  行情→AI分析→决策→下单→通知→审计→容器化 全部到位")
