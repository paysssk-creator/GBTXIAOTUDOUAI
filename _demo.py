import json,urllib.request,sys
sys.stdout.reconfigure(encoding='utf-8')

BASE="http://localhost:8765"
def get(path):
    return json.loads(urllib.request.urlopen(BASE+path).read().decode('utf-8'))

print("="*60)
print("  GBT Pro v2.1 - AI Trading Demo Panel")
print("="*60)

# Market
d=get("/api/market")
print("\nReal-time A-Share Market:")
for i in d['indices']:
    arrow = "^" if i['changePct']>0 else "v"
    print(f"  {arrow} {i['name']:8} {i['price']:10.2f}  {i['changePct']:+.2f}%")

# Status
d=get("/api/status")
print(f"\nEngine: {d['llm']} ({d['model']}) | MCP: {d['mcp_count']} servers | Keys: {d['keys_available']}/{d['keys_total']}")

# Agent counts
d=get("/api/agents/status")
a=d['agents']['agents']
print(f"\nAgent Cluster: {d['agents']['agents_running']} online | Total: {d['agents']['total_capabilities']} caps")
for name,info in a.items():
    caps=info['capabilities']
    print(f"  [{name}] {len(caps)} | {info['description']}")

print("\n"+"="*60)
print("  Open http://localhost:8765 to start trading")
print("="*60)
