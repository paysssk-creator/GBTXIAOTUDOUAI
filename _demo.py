import json,urllib.request,sys
sys.stdout.reconfigure(encoding='utf-8')

BASE="http://localhost:8765"
def get(path):
    try:
        return json.loads(urllib.request.urlopen(BASE+path, timeout=5).read().decode('utf-8'))
    except Exception as e:
        print(f"  ⚠️ API不可达: {path} ({e})")
        return None

print("="*60)
print("  GBT Pro v2.1 - AI Trading Demo Panel")
print("="*60)

# Market
d=get("/api/market")
if d and d.get("indices"):
    print("\nReal-time A-Share Market:")
    for i in d['indices']:
        arrow = "^" if i.get('changePct',0)>0 else "v"
        print(f"  {arrow} {i.get('name','?'):8} {i.get('price',0):10.2f}  {i.get('changePct',0):+.2f}%")
else:
    print("\n  ⚠️ 行情数据不可用 — 请确认服务已启动 (python s.py)")

# Status
d=get("/api/status")
if d:
    print(f"\nEngine: {d.get('llm','N/A')} ({d.get('model','N/A')}) | MCP: {d.get('mcp_count',0)} servers | Keys: {d.get('keys_available',0)}/{d.get('keys_total',0)}")
else:
    print("\n  ⚠️ 状态查询失败")

# Agent counts
d=get("/api/agents/status")
if d and d.get("agents"):
    a=d['agents'].get('agents',{})
    print(f"\nAgent Cluster: {d['agents'].get('agents_running',0)} online | Total: {d['agents'].get('total_capabilities',0)} caps")
    for name,info in a.items():
        caps=info.get('capabilities',[])
        print(f"  [{name}] {len(caps) if isinstance(caps,list) else caps} | {info.get('description','')}")
else:
    print("\n  ⚠️ Agent状态不可用")

print("\n"+"="*60)
print("  Open http://localhost:8765 to start trading")
print("="*60)
