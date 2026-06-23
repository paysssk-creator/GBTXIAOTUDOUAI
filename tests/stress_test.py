import subprocess, time, requests, os, sys, concurrent.futures, statistics
BASE = "http://127.0.0.1:8765"
def start():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.Popen([sys.executable, "-m", "gbt.web_api"], env=env)
def request_one(i):
    t0 = time.time()
    endpoint = "/api/health" if i % 2 == 0 else "/api/capabilities"
    try:
        r = requests.get(f"{BASE}{endpoint}", timeout=10)
        ok = r.status_code == 200
    except Exception as e:
        return (i, False, str(e), 0)
    return (i, ok, r.status_code, time.time()-t0)
def main():
    p = start(); time.sleep(3)
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(f"Stress test: {N} requests, {workers} concurrent workers")
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(request_one, range(N)))
    total = time.time() - t0
    passed = sum(1 for _, ok, _, _ in results if ok)
    latencies = [lat for _, _, _, lat in results if lat]
    print(f"Total time: {total:.2f}s | RPS: {N/total:.1f}")
    print(f"Passed: {passed}/{N} ({100*passed/N:.1f}%)")
    if latencies:
        print(f"Latency min/avg/max: {min(latencies)*1000:.1f}/{statistics.mean(latencies)*1000:.1f}/{max(latencies)*1000:.1f} ms")
    p.terminate(); p.wait(timeout=3)
if __name__ == "__main__":
    main()
