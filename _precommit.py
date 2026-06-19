"""
_precommit.py — GBT 提交前强制检查
运行: python _precommit.py
"""
import sys, io, os, glob, json, urllib.request, subprocess, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'C:\Users\ADMIN\Desktop\GBT-local'
PY312 = r'C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe'
API = 'http://localhost:8877'
PASS, FAIL = 0, 0

def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ [{name}] {detail}")
    else:
        FAIL += 1
        print(f"  ❌ [{name}] {detail}")
    return ok

print("=" * 55)
print("  GBT PRE-COMMIT CHECKLIST (7 steps)")
print("=" * 55)

# ── 1. py_compile ──
print("\n[1/6] py_compile 全量")
try:
    import py_compile
    py_files = glob.glob(os.path.join(ROOT, '**', '*.py'), recursive=True)
    py_files = [f for f in py_files if 'build' not in f and 'dist' not in f 
                and 'venv' not in f and '__pycache__' not in f]
    for f in sorted(py_files):
        py_compile.compile(f, doraise=True)
    check("compile", True, f"{len(py_files)} files clean")
except py_compile.PyCompileError as e:
    check("compile", False, str(e)[:80])

# ── 2. Router test ──
print("\n[2/6] 路由回归测试")
r = subprocess.run([PY312, os.path.join(ROOT, 'tests', 'test_router.py')],
                   capture_output=True, text=True, timeout=120, errors='replace')
output1 = r.stdout + r.stderr
ok1 = r.returncode == 0

r2 = subprocess.run([PY312, os.path.join(ROOT, 'tests', 'test_router_keywords.py')],
                    capture_output=True, text=True, timeout=120, errors='replace')
output2 = r2.stdout + r2.stderr
ok2 = r2.returncode == 0

if ok1 and ok2:
    check("router", True, f"regression + keywords: {output1.strip().split(chr(10))[-1] if output1.strip() else '?'} / {output2.strip().split(chr(10))[-1] if output2.strip() else '?'}")
elif not ok1:
    check("router", False, f"regression FAIL: {output1[:120]}")
else:
    check("router", False, f"keywords FAIL: {output2[:120]}")

# ── 3. API smoke test ──
print("\n[3/6] API 冒烟测试")
try:
    eps = ["/api/status", "/api/brain/status", "/api/trader/status", 
           "/api/watcher/status", "/api/trader/journal", "/api/trader/sessions",
           "/api/framework/status", "/api/framework/agents", "/api/framework/context"]
    ok_count = 0
    for ep in eps:
        urllib.request.urlopen(f'{API}{ep}', timeout=5)
        ok_count += 1
    check("api", ok_count == len(eps), f"{ok_count}/{len(eps)} endpoints reachable")
except Exception as e:
    check("api", False, str(e)[:60])

# ── 4. Data verification ──
print("\n[4/6] 数据真实性验证")
try:
    data_ok = True
    # brain
    b = json.loads(urllib.request.urlopen(f'{API}/api/brain/status', timeout=5).read())
    if not b.get('running'):
        data_ok = False
        print("    brain not running")

    # trader
    t = json.loads(urllib.request.urlopen(f'{API}/api/trader/status', timeout=5).read())
    if not isinstance(t.get('auto_trade'), bool):
        data_ok = False
        print("    trader auto_trade not bool")

    # watcher
    w = json.loads(urllib.request.urlopen(f'{API}/api/watcher/status', timeout=5).read())
    monitors = w.get('monitors', {})
    if len(monitors) < 6:
        data_ok = False
        print(f"    watcher only {len(monitors)} monitors")
    offline = [n for n,m in monitors.items() if m.get('status') != 'ok']
    check("data", data_ok, f"watcher: {len(offline)} alerts")
    
    # framework (new)
    try:
        fw = json.loads(urllib.request.urlopen(f'{API}/api/framework/status', timeout=5).read())
        agents = fw.get('agents', {})
        if len(agents) < 5:
            print(f"    framework only {len(agents)} agents (expected 5)")
    except:
        pass
except Exception as e:
    check("data", False, str(e)[:60])

# ── 5. Restart check ──
print("\n[5/6] GBT 进程状态")
try:
    import psutil
    py_procs = [p for p in psutil.process_iter(['pid','name','create_time']) 
                if p.info['name'] and 'python' in p.info['name'].lower()]
    recent = [p for p in py_procs if p.info['create_time'] and 
              time.time() - p.info['create_time'] < 86400]
    check("process", len(recent) > 0, f"{len(recent)} Python processes today")
except ImportError:
    check("process", True, "psutil not available, skipping")

# ── 6. Edge case test ──
print("\n[6/6] 路由边界测试")
edge_cases = [
    ("我要买000001", "auto_trade"),
    ("卖出600519", "auto_trade"),
    ("系统状态", "system_status"),
    ("监控", "watcher_check"),
    ("账户", "account_query"),
]
edge_ok = 0
for text, expected in edge_cases:
    try:
        data = json.dumps({"text": text, "mode": "CHAIN"}).encode()
        req = urllib.request.Request(f'{API}/api/reason', data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=10)
        result = json.loads(r.read())
        cap = result.get("capability", "")
        if cap == expected:
            edge_ok += 1
        else:
            print(f"    {text} → {cap} (expect {expected})")
    except Exception as e:
        print(f"    {text}: {e}")
check("edge", edge_ok == len(edge_cases), f"{edge_ok}/{len(edge_cases)} correct")

# ── Final ──
print(f"\n{'='*55}")
total = PASS + FAIL
print(f"  RESULT: {PASS}/{total} PASS")
if FAIL == 0:
    print("  ✅ READY TO COMMIT")
else:
    print(f"  ❌ {FAIL} failures — fix before commit")
print(f"{'='*55}")
sys.exit(0 if FAIL == 0 else 1)
