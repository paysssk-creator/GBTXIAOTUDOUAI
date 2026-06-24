"""
capability_stress_test.py — GBT 能力模块端到端压力测试

测试策略：
1. 独立扫描：每个能力模块逐个调用，确认可正常返回。
2. 统一调度：多模块并发调用，验证路由/后端稳定性。
3. 输出：每个模块 pass/fail、延迟、错误信息、汇总报告。

运行：python tests/capability_stress_test.py
"""
import os
import sys
import time
import json
import statistics
import concurrent.futures
import requests
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable

BASE = "http://127.0.0.1:8765"

def now():
    return time.strftime("%H:%M:%S")

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
            ok = bool(resp.get("ok"))
            preview = json.dumps(resp.get("data", resp), ensure_ascii=False)[:200]
            return TestResult(name, ok, latency, 200, "", preview)
        except Exception as e:
            latency = (time.time() - t0) * 1000
            return TestResult(name, False, latency, 0, str(e)[:200], "")

    # ── 模块测试函数 ──
    def test_health(self):
        return self._run_one("health", self._get, "/api/health")

    def test_metrics(self):
        return self._run_one("metrics", self._get, "/api/metrics")

    def test_dashboard(self):
        return self._run_one("dashboard", self._get, "/api/dashboard")

    def test_market(self):
        return self._run_one("market", self._get, "/api/market")

    def test_capabilities(self):
        return self._run_one("capabilities", self._get, "/api/capabilities")

    def test_chat(self):
        return self._run_one("chat", self._post, "/api/chat", {"text": "你好，GBT"})

    def test_desk_observe(self):
        return self._run_one("desk/observe", self._post, "/api/desk/observe")

    def test_desk_act_type(self):
        # 安全动作：输入一段无风险的文本到当前焦点（记事本等），随后回车
        return self._run_one("desk/act/type", self._post, "/api/desk/act", {
            "action_type": "type",
            "params": {"text": "GBT stress test", "interval": 0.01}
        })

    def test_desk_act_hotkey(self):
        # 安全组合键：复制（不破坏内容）
        return self._run_one("desk/act/hotkey", self._post, "/api/desk/act", {
            "action_type": "hotkey",
            "params": {"keys": ["ctrl", "c"]}
        })

    def test_desk_run_task(self):
        # 限制步数，避免长时间运行
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

    def test_watcher(self):
        return self._run_one("watcher", self._get, "/api/watcher")

    def test_cradle_status(self):
        return self._run_one("cradle/status", self._get, "/api/cradle/status")

    def test_screenpipe_status(self):
        return self._run_one("screenpipe/status", self._get, "/api/screenpipe/status")

    def test_nanobrowser_status(self):
        return self._run_one("nanobrowser/status", self._get, "/api/nanobrowser/status")

    def test_trade_analyze(self):
        return self._run_one("trade/analyze", self._post, "/api/trade/analyze", {"code": "600519"})

    def test_hacker_screen_ocr(self):
        return self._run_one("hacker/screen_ocr", self._post, "/api/hacker/exec", {
            "command": "screen_ocr"
        })

    def test_evolve(self):
        # evolve 是全盘扫描，单独给 60 秒超时
        return self._run_one("evolve", self._post, "/api/evolve", {"goal": "优化测试流程"}, timeout=60)

    def test_guard(self):
        # guard 是全盘安全扫描，单独给 60 秒超时
        return self._run_one("guard", self._post, "/api/guard", timeout=60)

    def test_keys_import(self):
        return self._run_one("keys/import", self._post, "/api/keys/import")

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

    def get_all_tests(self) -> List[Callable]:
        return [
            self.test_health,
            self.test_metrics,
            self.test_dashboard,
            self.test_market,
            self.test_capabilities,
            self.test_chat,
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
            self.test_watcher,
            self.test_cradle_status,
            self.test_screenpipe_status,
            self.test_nanobrowser_status,
            self.test_trade_analyze,
            self.test_hacker_screen_ocr,
            self.test_evolve,
            self.test_guard,
            self.test_keys_import,
            self.test_device_probe,
            self.test_device_speak,
            self.test_device_notify,
            self.test_device_camera,
            self.test_device_mic,
        ]

    def run_module_by_module(self):
        print(f"[{now()}] 开始模块独立扫描测试，共 {len(self.get_all_tests())} 个模块")
        for fn in self.get_all_tests():
            res = fn()
            self.results.append(res)
            status = "PASS" if res.ok else "FAIL"
            print(f"  [{status}] {res.module:<22} {res.latency_ms:>8.1f}ms {res.error}")
        return self.results

    def get_stress_tests(self) -> List[Callable]:
        """统一压力测试用例：排除 evolve/guard 等一次性全盘扫描重任务。"""
        heavy = {self.test_evolve, self.test_guard}
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
        print("\n" + "="*70)
        print(f"GBT 能力模块端到端压力测试报告")
        print(f"时间: {now()}")
        print(f"后端: {self.base}")
        print(f"总样本: {total} | 通过: {passed} | 失败: {total-passed} | 通过率: {100*passed/total:.1f}%")
        if all_results:
            latencies = [r.latency_ms for r in all_results]
            print(f"平均延迟: {statistics.mean(latencies):.1f}ms | 最大延迟: {max(latencies):.1f}ms")
        failed = [r for r in all_results if not r.ok]
        if failed:
            print("\n失败模块明细:")
            for r in failed:
                print(f"  - {r.module}: {r.error}")
        print("="*70)
        # 写 JSON 报告
        report_path = os.path.join(os.path.dirname(__file__), "capability_stress_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "base": self.base,
                "time": now(),
                "summary": {"total": total, "passed": passed, "failed": total-passed},
                "module_results": [asdict(r) for r in self.results],
                "stress_results": [asdict(r) for r in (stress_results or [])],
            }, f, ensure_ascii=False, indent=2)
        print(f"报告已保存: {report_path}")


def main():
    tester = CapabilityStressTest()
    # 1. 模块独立扫描
    tester.run_module_by_module()
    # 2. 统一智能调度全量压力
    stress = tester.run_unified_stress(workers=4, rounds=40)
    # 3. 输出报告
    tester.print_report(stress)


if __name__ == "__main__":
    main()
