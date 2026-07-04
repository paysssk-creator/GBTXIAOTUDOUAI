"""GBT v2.0 End-to-End Stress Test"""
import requests, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

CASES = [
    ('screenshot', '截图'),
    ('voice_list', '列出声音'),
    ('market_scan', '行情大盘'),
    ('stock_lookup', '600519'),
    ('browser_open', '打开百度'),
    ('account_query', '账户'),
    ('system_status', '系统状态'),
    ('window_maximize', '最大化窗口'),
    ('watchlist', '自选池'),
    ('watcher_check', '守夜人'),
    ('notify', '通知测试'),
    ('voice_speak', '说话你好我是GBT'),
]

URL = 'http://127.0.0.1:8765/api/reason'
CONCURRENT = 10
ROUNDS = 3


def call_api(ability, text, round_no):
    t0 = time.time()
    try:
        r = requests.post(URL, json={'text': text, 'mode': 'quick'}, timeout=60)
        elapsed = time.time() - t0
        d = r.json()
        cap = d.get('capability', '')
        match = cap == ability
        return {
            'ability': ability, 'round': round_no,
            'ok': True, 'matched': match, 'cap': cap,
            'elapsed': elapsed, 'status_code': r.status_code,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            'ability': ability, 'round': round_no,
            'ok': False, 'matched': False, 'error': str(e)[:80],
            'elapsed': elapsed,
        }


results = []
errors = []
t0_overall = time.time()

for rnd in range(1, ROUNDS + 1):
    tasks = []
    for ability, text in CASES:
        for _ in range(CONCURRENT):
            tasks.append((ability, text, rnd))

    print(f"Round {rnd}: {len(tasks)} concurrent requests...")
    rnd_t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(50, len(tasks))) as pool:
        futures = {pool.submit(call_api, a, t, r): (a, t) for a, t, r in tasks}
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            if not r['ok']:
                errors.append(r)
    print(f"  Done in {time.time() - rnd_t0:.1f}s")

overall = time.time() - t0_overall

# Stats
total = len(results)
ok_count = sum(1 for r in results if r['ok'])
fail_count = total - ok_count
matched = sum(1 for r in results if r.get('matched'))
routing_pct = matched / max(ok_count, 1) * 100

elapsed_times = [r['elapsed'] for r in results if r['ok']]
avg_latency = sum(elapsed_times) / max(len(elapsed_times), 1) if elapsed_times else 0
max_latency = max(elapsed_times) if elapsed_times else 0
min_latency = min(elapsed_times) if elapsed_times else 0

by_ability = defaultdict(lambda: {'total': 0, 'ok': 0, 'matched': 0, 'times': []})
for r in results:
    a = r['ability']
    by_ability[a]['total'] += 1
    if r['ok']:
        by_ability[a]['ok'] += 1
        by_ability[a]['times'].append(r['elapsed'])
    if r.get('matched'):
        by_ability[a]['matched'] += 1

print()
print("=" * 60)
print("  GBT v2.0 E2E Stress Test Report")
print("=" * 60)
print(f"  Total requests:    {total}  (12 abilities x {CONCURRENT} concurrent x {ROUNDS} rounds)")
print(f"  Overall time:      {overall:.1f}s")
print(f"  Success rate:      {ok_count}/{total} ({ok_count*100/total:.1f}%)")
print(f"  Routing accuracy:  {matched}/{ok_count} ({routing_pct:.1f}%)")
print(f"  Avg latency:       {avg_latency*1000:.0f}ms")
print(f"  Min latency:       {min_latency*1000:.0f}ms")
print(f"  Max latency:       {max_latency*1000:.0f}ms")
print(f"  Throughput:        {total/overall:.1f} req/s")
print()

print("=" * 60)
print("  Per-Ability Breakdown")
print("=" * 60)
header = f"  {'Ability':20s} {'Total':>5s} {'OK':>5s} {'Match':>7s} {'Avg':>7s} {'Max':>7s}"
print(header)
print("  " + "-" * (len(header) - 2))
for a in sorted(by_ability.keys()):
    d = by_ability[a]
    ok = d['ok']
    t = d['total']
    times = d['times']
    avg = sum(times) / len(times) * 1000 if times else 0
    mx = max(times) * 1000 if times else 0
    line = f"  {a:20s} {t:5d} {ok:5d} {d['matched']:4d}/{ok:<3d} {avg:6.0f}ms {mx:6.0f}ms"
    print(line)

if errors:
    print()
    print(f"  ERRORS: {len(errors)}")
    for e in errors[:5]:
        print(f"    [{e['ability']}] {e.get('error','?')}")

print()
if ok_count == total and matched == ok_count:
    print("  VERDICT: ALL PASS -- production ready")
elif fail_count > total * 0.05:
    print(f"  VERDICT: FAIL -- {fail_count} errors > 5% threshold")
else:
    print("  VERDICT: WARN -- minor issues, review errors above")
