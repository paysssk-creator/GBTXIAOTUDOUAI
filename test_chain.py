# GBT Pro v2.1 Full Chain Self-Test
import urllib.request, json, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8877'

def get(path, timeout=8):
    r = urllib.request.urlopen(f'{BASE}{path}', timeout=timeout)
    return json.loads(r.read())

def post(path, data=None, timeout=15):
    d = json.dumps(data or {}).encode() if data else b'{}'
    r = urllib.request.urlopen(f'{BASE}{path}', data=d, timeout=timeout,
        headers={'Content-Type': 'application/json'})
    return json.loads(r.read())

results = {'pass': 0, 'fail': 0, 'skip': 0}

def check(name, condition, detail=''):
    if condition:
        results['pass'] += 1
        print(f'  [PASS] {name}')
    else:
        results['fail'] += 1
        print(f'  [FAIL] {name} - {detail}')

print('=== GBT Pro v2.1 Full Chain Self-Test ===')

# 1. Status
print('\n1. System Status')
s = get('/api/status')
check('LLM ready', s.get('llm') not in (None, '', 'offline'))
check('MCP >= 10', s.get('mcp_count', 0) >= 10, f"mcp_count={s.get('mcp_count')}")

# 2. Brain
print('\n2. Autonomous Brain')
b = get('/api/brain/status')
check('Brain running', b.get('running'))
hb = b.get('heartbeat', {})
check('Heartbeat > 0', hb.get('count', 0) > 0, f"count={hb.get('count')}")
check('Capabilities >= 5', len(b.get('capabilities', [])) >= 5,
      f"capabilities={len(b.get('capabilities',[]))}")

# 3. Watcher
print('\n3. Night Watcher')
w = get('/api/watcher/status')
check('Watcher running', w.get('running'))
monitors = w.get('monitors', {})
check('8 monitors', len(monitors) >= 8, f"only {len(monitors)}")
for src in ['network', 'process', 'filesystem', 'registry', 'wifi', 'disk', 'logs', 'connections']:
    m = monitors.get(src, {})
    st = m.get('status', '?')
    check(f'  {src}', st in ('ok', 'idle', 'warn'), f'status={st}')

# 4. Trader
print('\n4. Trading Engine')
t = get('/api/trader/status')
check('Auto trade ON', t.get('auto_trade'))
check('Watchlist > 0', t.get('watchlist_count', 0) > 0)
check('Confidence >= 50', t.get('min_confidence', 0) >= 50, f"conf={t.get('min_confidence')}")

# 5. Account (use /api/account not /api/account/summary)
print('\n5. Sim Account')
try:
    ac = get('/api/account')
    check('Cash > 0', ac.get('cash', 0) > 0, f"cash={ac.get('cash')}")
    check('Initial 100k', ac.get('initial_cash', 0) == 100000)
except Exception as e:
    check('Account API', False, str(e))

# 6. Dashboard
print('\n6. Dashboard')
try:
    db = get('/api/dashboard')
    check('Dashboard data', len(db) > 0, f"keys={len(db)}")
except Exception as e:
    check('Dashboard API', False, str(e))

# 7. Risk
print('\n7. Risk Control')
try:
    rk = post('/api/risk/check', {
        'code': 'sh600519', 'action': 'buy', 'price': 1000,
        'shares': 100, 'confidence': 75
    })
    check('Risk check OK', rk.get('ok') or rk.get('approved'),
          f"response={str(rk)[:100]}")
except Exception as e:
    check('Risk API', False, str(e))

# 8. Brain context
print('\n8. Brain Context')
try:
    ctx = get('/api/brain/context')
    check('Context data', isinstance(ctx, list) or isinstance(ctx, dict),
          f"type={type(ctx).__name__}")
except Exception as e:
    check('Context API', False, str(e))

# Summary
total = results['pass'] + results['fail'] + results['skip']
print(f'\n=== Result: {results["pass"]}/{total} PASS, {results["fail"]} FAIL, {results["skip"]} SKIP ===')
if results['fail'] > 0:
    print('FAILURES DETECTED - review above')
sys.exit(0 if results['fail'] == 0 else 1)
