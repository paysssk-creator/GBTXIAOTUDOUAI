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

print('=== GBT Pro v2.1 全链路自测 ===')

# 1. Status
print('\n1. 系统状态')
s = get('/api/status')
check('API可达', s.get('status') == 'running')
check('LLM就绪', s.get('llm') not in (None, '', 'offline'))
check('MCP服务器', s.get('mcp_count', 0) >= 10)

# 2. Brain
print('\n2. 自主大脑')
b = get('/api/brain/status')
check('大脑运行', b.get('running'))
check('心跳计数>0', b.get('heartbeat', {}).get('count', 0) > 0,
      f"count={b.get('heartbeat', {}).get('count', 0)}")
check('能力注册', len(b.get('capabilities', [])) >= 5,
      f"capabilities={len(b.get('capabilities',[]))}")
check('上下文记录', len(b.get('context', [])) > 0,
      f"context={len(b.get('context',[]))}")

# 3. Watcher
print('\n3. 守夜人')
w = get('/api/watcher/status')
check('守夜人运行', w.get('running'))
monitors = w.get('monitors', {})
check('8个监控点', len(monitors) >= 8, f"只有{len(monitors)}")
for src in ['network', 'process', 'filesystem', 'registry', 'wifi', 'disk', 'logs', 'connections']:
    m = monitors.get(src, {})
    st = m.get('status', '?')
    check(f'  {src}', st in ('ok', 'idle', 'warn'), f'status={st}')

# 4. Trader
print('\n4. 交易引擎')
t = get('/api/trader/status')
check('自主交易开启', t.get('auto_trade'))
check('自选股数>0', t.get('watchlist_count', 0) > 0)
check('最低置信度', t.get('min_confidence', 0) >= 50)

# 5. Account
print('\n5. 模拟账户')
ac = get('/api/account/summary')
check('初始资金', ac.get('initial_cash', 0) == 100000)
check('现金>0', ac.get('cash', 0) > 0)

# 6. Risk
print('\n6. 风控')
rk = get('/api/risk/status')
check('止损比例', rk.get('stop_loss_pct', 0) > 0)
check('最高仓位', rk.get('max_single_pct', 0) > 0)

# 7. Pipeline (with AI analysis - skip if LLM not available)
print('\n7. 分析流水线')
try:
    p = post('/api/trader/pipeline', {'code': 'sh600519'})
    steps = p.get('steps', [])
    check('流水线步骤>0', len(steps) > 0, f'steps={len(steps)}')
    completed = sum(1 for s in steps if s.get('status') == 'completed')
    check('至少1步完成', completed >= 1, f'completed={completed}/{len(steps)}')
except Exception as e:
    results['skip'] += 1
    print(f'  [SKIP] Pipeline分析: {e}')

# Summary
print(f'\n=== 结果: {results["pass"]}PASS / {results["fail"]}FAIL / {results["skip"]}SKIP ===')
sys.exit(0 if results['fail'] == 0 else 1)
