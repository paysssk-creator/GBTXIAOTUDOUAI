"""
capability_stress_test.py — GBT 本地 APP 启动 + 能力模块端到端测试

测试策略：
1. 启动等待：先等待后端 http://127.0.0.1:8765 就绪。
2. 核心启动项：health、status、capabilities、config、skills 等。
3. 交易能力：account、trade/analyze、trade/execute、skill/* 交易相关。
4. 本地设备能力：device/probe、speak、notify、camera、mic。
5. 输出：每个模块 pass/fail、延迟、错误信息、汇总报告。

运行：python tests/capability_stress_test.py
"""
import os
import sys

# Force UTF-8 on Windows so Chinese logs do not mojibake
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

# Set Windows console code page to UTF-8 if possible
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

import time
import json
import statistics
import concurrent.futures
import requests
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable

BASE = "http://127.0.0.1:8765"
STARTUP_TIMEOUT = 30  # 等待后端启动的最大秒数


def now():
    return time.strftime("%H:%M:%S")


def wait_for_backend(base: str = BASE, timeout: int = STARTUP_TIMEOUT):
    """等待后端服务就绪"""
    print(f"[{now()}] 等待后端 {base} 就绪...")
    for i in range(timeout):
        try:
            r = requests.get(f"{base}/api/health", timeout=2)
            if r.status_code == 200:
                print(f"[{now()}] 后端已就绪 ( waited {i + 1}s )")
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"后端 {base} 在 {timeout}s 内未就绪")


@dataclass
class TestResult:
    module: str
    ok: bool
    latency_ms: float
    status_code: int = 0
    error: str = ""
    payload_preview: str = ""


class CapabilityStressTest:
    def __init__(self, base: str = BASE):
        self.base = base
        self.results: List[TestResult] = []

    def _post(self, path: str, payload: Dict = None, timeout: int = 30) -> Dict:
        r = requests.post(f"{self.base}{path}", json=payload or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _get(self, path: str, timeout: int = 30) -> Dict:
        r = requests.get(f"{self.base}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _run_one(self, name: str, fn: Callable, *args, **kwargs) -> TestResult:
        t0 = time.time()
        try:
            resp = fn(*args, **kwargs)
            latency = (time.time() - t0) * 1000
            ok = bool(resp.get("ok")) if isinstance(resp, dict) else True
            preview = json.dumps(resp.get("data", resp) if isinstance(resp, dict) else resp, ensure_ascii=False)[:200]
            return TestResult(name, ok, latency, 200, "", preview)
        except Exception as e:
            latency = (time.time() - t0) * 1000
            return TestResult(name, False, latency, 0, str(e)[:200], "")

    # ── 启动与核心能力 ──
    def test_health(self):
        return self._run_one("health", self._get, "/api/health")

    def test_status(self):
        return self._run_one("status", self._get, "/api/status")

    def test_config(self):
        return self._run_one("config", self._get, "/api/config")

    def test_metrics(self):
        return self._run_one("metrics", self._get, "/api/metrics")

    def test_dashboard(self):
        return self._run_one("dashboard", self._get, "/api/dashboard")

    def test_market(self):
        return self._run_one("market", self._get, "/api/market")

    def test_capabilities(self):
        return self._run_one("capabilities", self._get, "/api/capabilities")

    def test_skills_list(self):
        return self._run_one("skills/list", self._get, "/api/skills")

    def test_chat(self):
        return self._run_one("chat", self._post, "/api/chat", {"text": "你好，GBT"})

    # ── 交易与 A股能力 ──
    def test_trade_analyze(self):
        return self._run_one("trade/analyze", self._post, "/api/trade/analyze", {"code": "600519"})

    def test_trade_execute(self):
        return self._run_one("trade/execute", self._post, "/api/trade/execute", {
            "code": "sh600519", "action": "analyze", "shares": 100
        })

    def test_skill_account_query(self):
        return self._run_one("skill/account_query", self._post, "/api/skill/account_query", {"text": "查账户"})

    def test_skill_stock_lookup(self):
        return self._run_one("skill/stock_lookup", self._post, "/api/skill/stock_lookup", {"text": "查询 600519"})

    def test_skill_scan_market(self):
        return self._run_one("skill/scan_market", self._post, "/api/skill/scan_market", {"text": "扫描市场"})

    def test_skill_trade(self):
        return self._run_one("skill/trade", self._post, "/api/skill/trade", {"text": "分析 贵州茅台"})

    def test_skill_watchlist(self):
        return self._run_one("skill/watchlist", self._post, "/api/skill/watchlist", {"text": "自选股"})

    # ── 桌面与浏览器能力 ──
    def test_desk_observe(self):
        return self._run_one("desk/observe", self._post, "/api/desk/observe")

    def test_desk_act_type(self):
        return self._run_one("desk/act/type", self._post, "/api/desk/act", {
            "action_type": "type",
            "params": {"text": "GBT stress test", "interval": 0.01}
        })

    def test_desk_act_hotkey(self):
        return self._run_one("desk/act/hotkey", self._post, "/api/desk/act", {
            "action_type": "hotkey",
            "params": {"keys": ["ctrl", "c"]}
        })

    def test_desk_run_task(self):
        return self._run_one("desk/run_task", self._post, "/api/desk/run_task", {
            "task": "截图观察桌面", "max_steps": 2
        })

    def test_browser_open(self):
        return self._run_one("chat/browser", self._post, "/api/chat", {
            "text": "打开浏览器访问 bing.com"
        })

    def test_web_search(self):
        return self._run_one("chat/search", self._post, "/api/chat", {
            "text": "搜索 贵州茅台 最新消息"
        })

    def test_notify(self):
        return self._run_one("chat/notify", self._post, "/api/chat", {
            "text": "通知我 测试完成"
        })

    def test_voice_speak(self):
        return self._run_one("chat/voice", self._post, "/api/chat", {
            "text": "朗读 压力测试开始"
        })

    def test_file_operation(self):
        return self._run_one("chat/file", self._post, "/api/chat", {
            "text": "读取文件 README.md"
        })

    def test_system_status(self):
        return self._run_one("chat/system", self._post, "/api/chat", {
            "text": "查看系统状态"
        })

    # ── 监控与管道能力 ──
    def test_watcher(self):
        return self._run_one("watcher", self._get, "/api/watcher")

    def test_cradle_status(self):
        return self._run_one("cradle/status", self._get, "/api/cradle/status")

    def test_screenpipe_status(self):
        return self._run_one("screenpipe/status", self._get, "/api/screenpipe/status")

    def test_nanobrowser_status(self):
        return self._run_one("nanobrowser/status", self._get, "/api/nanobrowser/status")

    # ── 设备能力 ──
    def test_device_probe(self):
        return self._run_one("device/probe", self._get, "/api/device/probe")

    def test_device_speak(self):
        return self._run_one("device/speak", self._post, "/api/device/speak", {"text": "设备能力测试"})

    def test_device_notify(self):
        return self._run_one("device/notify", self._post, "/api/device/notify", {"title": "GBT", "message": "设备通知测试"})

    def test_device_camera(self):
        return self._run_one("device/camera", self._post, "/api/device/camera", {"index": 0})

    def test_device_mic(self):
        return self._run_one("device/mic", self._post, "/api/device/mic", {"seconds": 1.0})

    # ── 安全/进化能力（重任务，单独处理） ──
    def test_hacker_screen_ocr(self):
        return self._run_one("hacker/screen_ocr", self._post, "/api/hacker/exec", {
            "command": "screen_ocr"
        })

    def test_evolve(self):
        return self._run_one("evolve", self._post, "/api/evolve", {"goal": "优化测试流程"}, timeout=60)

    def test_guard(self):
        return self._run_one("guard", self._post, "/api/guard", timeout=60)

    def test_keys_import(self):
        return self._run_one("keys/import", self._post, "/api/keys/import")

    def get_all_tests(self) -> List[Callable]:
        return [
            # 启动与核心
            self.test_health,
            self.test_status,
            self.test_config,
            self.test_metrics,
            self.test_dashboard,
            self.test_market,
            self.test_capabilities,
            self.test_skills_list,
            self.test_chat,
            # 交易/A股
            self.test_trade_analyze,
            self.test_trade_execute,
            self.test_skill_account_query,
            self.test_skill_stock_lookup,
            self.test_skill_scan_market,
            self.test_skill_trade,
            self.test_skill_watchlist,
            # 桌面/浏览器
            self.test_desk_observe,
            self.test_desk_act_type,
            self.test_desk_act_hotkey,
            self.test_desk_run_task,
            self.test_browser_open,
            self.test_web_search,
            self.test_notify,
            self.test_voice_speak,
            self.test_file_operation,
            self.test_system_status,
            # 监控/管道
            self.test_watcher,
            self.test_cradle_status,
            self.test_screenpipe_status,
            self.test_nanobrowser_status,
            # 设备
            self.test_device_probe,
            self.test_device_speak,
            self.test_device_notify,
            self.test_device_camera,
            self.test_device_mic,
            # 安全/进化
            self.test_hacker_screen_ocr,
            self.test_keys_import,
        ]

    def get_heavy_tests(self) -> List[Callable]:
        """耗时较长的全局扫描任务"""
        return [self.test_evolve, self.test_guard]

    def run_module_by_module(self, include_heavy: bool = False):
        tests = self.get_all_tests()
        if include_heavy:
            tests += self.get_heavy_tests()
        print(f"[{now()}] 开始模块独立扫描测试，共 {len(tests)} 个模块")
        for fn in tests:
            res = fn()
            self.results.append(res)
            status = "PASS" if res.ok else "FAIL"
            print(f"  [{status}] {res.module:<28} {res.latency_ms:>8.1f}ms {res.error}")
        return self.results

    def get_stress_tests(self) -> List[Callable]:
        """统一压力测试用例：排除 evolve/guard 等一次性全盘扫描重任务。"""
        heavy = set(self.get_heavy_tests())
        return [t for t in self.get_all_tests() if t not in heavy]

    def run_unified_stress(self, workers: int = 4, rounds: int = 40):
        """统一智能调度全量压力测试：从全部模块中随机抽取并发调用。"""
        import random
        tests = self.get_stress_tests()
        print(f"[{now()}] 开始统一调度全量压力测试: {rounds} 请求, {workers} 并发")
        stress_results: List[TestResult] = []

        def worker(i: int):
            fn = tests[i % len(tests)]
            return fn()

        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(worker, range(rounds)):
                stress_results.append(res)
        total = time.time() - t0
        passed = sum(1 for r in stress_results if r.ok)
        latencies = [r.latency_ms for r in stress_results]
        print(f"[{now()}] 统一调度完成: {passed}/{rounds} 通过, 总耗时 {total:.2f}s, RPS {rounds/total:.1f}")
        if latencies:
            print(f"  延迟 min/avg/max: {min(latencies):.1f}/{statistics.mean(latencies):.1f}/{max(latencies):.1f} ms")
        return stress_results

    def print_report(self, stress_results: List[TestResult] = None):
        all_results = self.results + (stress_results or [])
        passed = sum(1 for r in all_results if r.ok)
        total = len(all_results)
        print("\n" + "=" * 70)
        print(f"GBT 本地 APP 启动与能力模块端到端测试报告")
        print(f"时间: {now()}")
        print(f"后端: {self.base}")
        print(f"总样本: {total} | 通过: {passed} | 失败: {total - passed} | 通过率: {100 * passed / total:.1f}%")
        if all_results:
            latencies = [r.latency_ms for r in all_results]
            print(f"平均延迟: {statistics.mean(latencies):.1f}ms | 最大延迟: {max(latencies):.1f}ms")
        failed = [r for r in all_results if not r.ok]
        if failed:
            print("\n失败模块明细:")
            for r in failed:
                print(f"  - {r.module}: {r.error}")
        print("=" * 70)
        # 写 JSON 报告
        report_path = os.path.join(os.path.dirname(__file__), "capability_stress_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "base": self.base,
                "time": now(),
                "summary": {"total": total, "passed": passed, "failed": total - passed},
                "module_results": [asdict(r) for r in self.results],
                "stress_results": [asdict(r) for r in (stress_results or [])],
            }, f, ensure_ascii=False, indent=2)
        print(f"报告已保存: {report_path}")


def main():
    wait_for_backend(BASE, STARTUP_TIMEOUT)
    tester = CapabilityStressTest()
    # 1. 模块独立扫描（不含重任务）
    tester.run_module_by_module(include_heavy=False)
    # 2. 统一智能调度全量压力
    stress = tester.run_unified_stress(workers=4, rounds=40)
    # 3. 输出报告
    tester.print_report(stress)


if __name__ == "__main__":
    main()
