"""
gbt_agent.py — GBT全能开发者Agent
集成所有MCP工具 + ReAct推理 + 记忆系统
"""

import os
from datetime import datetime
from typing import Optional, Iterator, List, Tuple, Dict, Any, Callable
from gbt.llm import GBTLLM
from gbt.tool import ToolRegistry
from gbt.agent import SimpleAgent, AgentConfig
from gbt.react import ReActAgent
from gbt.memory import MemoryManager
from gbt.evolve import EvolveEngine, EvolveReport, run_evolve
from gbt.guard import PreActionGuard, GuardReport, scan_all, guard_action, guard_deploy
from gbt.mirror import MirrorSpace, MirrorPipeline, RealCodeValidator, scan_fakes, mirror_run
from gbt.mcp import UniversalMCP, get_mcp, call_mcp
from gbt.reasoner import DeepReasoner, ReasonMode, ReasonResult
from gbt.winctl import get_winctl, WindowsController
from gbt.message import Message


# GBT系统提示词
GBT_SYSTEM_PROMPT = """你是 GBT小土豆全能开发者，一个AI原生的全能开发Agent。

## 核心能力
- 🔍 代码扫描与安全审计 (scanner)
- 📋 项目健康审计 (audit)
- 🧬 6步自进化闭环 (evolve)
- 📦 记忆管理 (memory)
- 🤖 云端LLM调度 (cloud_llm)
- 🔧 一键自动修复 (auto_fix)
- 🖥️ 桌面控制 (desktop)
- 📧 邮箱监控 (email)
- 🪞 镜像部署 (deploy)

## 工作原则
- 所有代码修改必须走6步闭环: 自查→扫描→备份→修复→审查→进化
- 禁止裸改代码，必须先git备份
- 金融数据必须来自真实API，禁止捏造

## 回复风格
- 简洁专业，用emoji标记关键信息
- 提供可执行的方案，而不是泛泛而谈
"""


class GBTAgent(SimpleAgent):
    """GBT全能开发者Agent — 集成所有能力的超体"""

    def __init__(self, llm: Optional[GBTLLM] = None,
                 provider: str = "auto", model: Optional[str] = None,
                 name: str = "GBTxiaotudou",
                 project_root: Optional[str] = None):
        # 初始化LLM
        self._llm = llm or GBTLLM(provider=provider, model=model)

        # 工具注册表
        self._tools = ToolRegistry()
        self._register_core_tools()

        # 记忆系统
        self.memory = MemoryManager()

        # 配置
        config = AgentConfig(name=name, max_steps=10,
                            max_tool_iterations=5, debug=False)

        super().__init__(name=name, llm=self._llm,
                        system_prompt=GBT_SYSTEM_PROMPT,
                        config=config, tool_registry=self._tools,
                        enable_tool_calling=True)

        self.project_root = project_root
        print(f"⚕ GBT {name} 全能开发者就绪！")

    def _register_core_tools(self):
        """注册核心工具"""
        # 基础工具
        self._tools.register("help", "显示帮助信息", self._tool_help,
                            {"action": "操作: help|tools|status"})
        self._tools.register("status", "显示当前状态", self._tool_status)
        self._tools.register("memory_set", "存储记忆 key value",
                            self._tool_memory_set,
                            {"key": "记忆键", "value": "记忆值"})
        self._tools.register("memory_get", "读取记忆 key",
                            self._tool_memory_get, {"key": "记忆键"})
        self._tools.register("evolve", "执行6步自进化闭环: 自查→扫描→备份→修复→审查→进化",
                            self._tool_evolve,
                            {"description": "进化描述", "dry_run": "干跑模式(true/false)"})
        self._tools.register("guard", "行动前强制全项目扫描守卫: scan|check|deploy",
                            self._tool_guard,
                            {"action": "scan/check/deploy"})
        self._tools.register("mirror", "镜像空间: 扫描虚假代码→镜像执行→验证→部署",
                            self._tool_mirror,
                            {"action": "scan|run|deploy"})
        self._tools.register("reason", "深度推理: 调用LLM算力全方位分析 chain|tree|swot|root_cause|decision|estimate|compare|plan",
                            self._tool_reason,
                            {"question": "推理问题", "mode": "推理模式"})
        self._tools.register("winctl", "Windows系统操控: screen/voice/bt/wifi/keyboard/mouse/volume/camera/notify/clipboard/lock/shutdown",
                            self._tool_winctl,
                            {"feature": "功能", "action": "操作", "params": "参数"})

    def _tool_help(self, action: str = "help") -> str:
        if action == "tools":
            return self._tools.get_tools_description()
        return ("GBT全能开发者工具:\n"
                "- help: 帮助\n- status: 状态\n"
                "- memory_set/memory_get: 记忆管理\n"
                "更多工具通过 add_tool() 动态注册")

    def _tool_status(self) -> str:
        mem = self.memory.stats()
        tools = len(self._tools)
        return (f"⚕ GBT {self.name}\n"
                f"LLM: {self.llm.provider_name}({self.llm.model})\n"
                f"工具: {tools}个\n"
                f"记忆: {mem['store']}持久/{mem['working']}工作")

    def _tool_memory_set(self, key: str, value: str) -> str:
        self.memory.set(key, value)
        return f"✅ 已记忆: {key}"

    def _tool_memory_get(self, key: str) -> str:
        v = self.memory.get(key)
        return str(v) if v else f"❌ 未找到: {key}"

    def _tool_evolve(self, description: str = "", dry_run: str = "false") -> str:
        """通过工具调用触发6步进化闭环"""
        is_dry = dry_run.lower() in ("true", "1", "yes")
        report = self.evolve(description, dry_run=is_dry)
        status = "✅ 成功" if report.success else "❌ 失败"
        steps_info = ", ".join(
            f"{s.name}={s.status.value}" for s in report.steps)
        return f"{status}\n{steps_info}\n{report.summary or '完成'}"

    def _tool_guard(self, action: str = "scan") -> str:
        """守卫工具 — 强制全项目扫描"""
        project = self.project_root or os.getcwd()
        if action == "check" or action == "bidirectional":
            guard = PreActionGuard(project, strict=True)
            pre, post = guard.bidirectional_check(action)
            return (f"前置: {pre.status.value}\n"
                    f"后置: {post.status.value}\n"
                    f"差异: {post.diff_summary}")
        elif action == "deploy":
            report = guard_deploy(project)
            return (f"部署检查: {report.status.value}\n"
                    f"框架: {'完整' if report.framework_check.get('ok') else '不完整'}")
        else:  # scan
            snapshot = scan_all(project)
            return (f"全扫描: {snapshot.total_files}文件 "
                    f"| {snapshot.issues_count}问题 "
                    f"| {snapshot.warnings_count}警告")

    def guard_scan(self) -> GuardReport:
        """行动前强制全项目扫描"""
        project = self.project_root or os.getcwd()
        guard = PreActionGuard(project, strict=True)
        return guard.pre_action_check("manual_guard")

    def _tool_mirror(self, action: str = "scan") -> str:
        """镜像工具: scan扫描虚假/run镜像执行/deploy部署"""
        project = self.project_root or os.getcwd()
        if action == "scan":
            issues = scan_fakes(project)
            return (f"虚假代码扫描: {len(issues)}问题\n" +
                    "\n".join(f"  {i.file}:{i.line} {i.description}"
                             for i in issues[:10]))
        elif action == "run":
            def fix_in_mirror(mirror, issues):
                for iss in issues:
                    mirror.write_file(iss.file, iss.snippet + "  # FIXED")
                return len(issues)
            reports = mirror_run(project, fix_in_mirror)
            return "\n".join(f"{r.stage.value}: {r.status} {r.details}" for r in reports)
        elif action == "deploy":
            ok, count = RealCodeValidator().is_fake_free(project)
            if ok:
                return f"✅ 无虚假代码，可安全部署 ({count}文件)"
            return f"❌ 仍有{count}个虚假代码，禁止部署"
        return f"未知操作: {action}"

    def mirror_scan(self) -> List:
        """扫描项目中的虚假代码"""
        project = self.project_root or os.getcwd()
        return scan_fakes(project)

    def mirror_deploy(self, fix_func=None) -> List:
        """镜像空间执行并部署"""
        project = self.project_root or os.getcwd()
        return mirror_run(project, fix_func)

    def call_mcp(self, server: str, method: str = "", args: str = ""):
        """万能MCP调用 — 调用任意MCP Server"""
        return call_mcp(server, method, args)

    def call_mcp_pipeline(self, steps: List[tuple]):
        """MCP管道调用"""
        return get_mcp().pipeline(steps)

    def _tool_winctl(self, feature: str="help", action: str="help", params: str="") -> str:
        """Windows系统操控工具"""
        wctl = get_winctl()
        if feature == "help" or action == "help":
            return wctl.help()
        kw = {}
        if params:
            for p in params.split(","):
                if "=" in p:
                    k, v = p.split("=", 1)
                    kw[k.strip()] = v.strip()
        r = wctl.call(feature, action, **kw)
        return f"{'✅' if r.ok else '❌'} {r.feature}.{r.action}: {r.data[:2000] if r.data else r.error}"

    def winctl(self, feature: str, action: str, **kw):
        """原生Windows操控"""
        return get_winctl().call(feature, action, **kw)

    def winctl_help(self) -> str:
        return get_winctl().help()

    def list_mcp_servers(self) -> List[str]:
        """列出所有MCP服务器"""
        return get_mcp().list_servers()

    def _tool_reason(self, question: str = "", mode: str = "chain") -> str:
        """深度推理工具 — 调用LLM算力分析"""
        mode_map = {m.value: m for m in ReasonMode}
        rm = mode_map.get(mode, ReasonMode.CHAIN)
        reasoner = DeepReasoner(self.llm, self._tools)
        reasoner = DeepReasoner(self.llm, self._tools)
        result = reasoner.reason(question, rm)
        return (f"## 推理结果 [{result.mode.value}] 置信度:{result.confidence:.0%}\n\n"
                f"{result.conclusion}\n\n"
                f"计划: {'; '.join(result.plan[:5]) if result.plan else '无'}")

    def deep_reason(self, question: str, mode: str = "chain",
                    context: str = "") -> ReasonResult:
        """深度推理 — 调用LLM真实算力全方位分析"""
        mode_map = {m.value: m for m in ReasonMode}
        rm = mode_map.get(mode, ReasonMode.CHAIN)
        reasoner = DeepReasoner(self.llm, self._tools)
        return reasoner.reason(question, rm, context)

    def reason_pipeline(self, question: str) -> Tuple:
        """完整推理管道: 根因→决策→计划"""
        reasoner = DeepReasoner(self.llm, self._tools)
        return reasoner.pipeline_reason(question)

    def reason_multi(self, question: str, modes: List[str] = None) -> List[ReasonResult]:
        """多模式交叉推理"""
        reasoner = DeepReasoner(self.llm, self._tools)
        if modes:
            rm_list = [ReasonMode(m) for m in modes]
        else:
            rm_list = None
        return reasoner.multi_reason(question, rm_list)

    # ── 便捷方法 ──

    def register_tool(self, name: str, desc: str, func, params=None):
        """注册外部工具(如MCP工具包装)"""
        self._tools.register(name, desc, func, params)

    def react_run(self, question: str, max_steps: int = 5) -> str:
        """使用ReAct模式运行"""
        react = ReActAgent(self.name, self.llm, self._tools,
                          max_steps=max_steps)
        return react.run(question)

    def chat(self, text: str) -> str:
        """对话模式"""
        return self.run(text)

    def chat_stream(self, text: str) -> Iterator[str]:
        """流式对话"""
        return self.stream_run(text)

    # ── 6步自进化闭环 ──

    def evolve(self, description: str = "", dry_run: bool = False,
               strong: bool = False) -> EvolveReport:
        """
        执行6步自进化闭环
        Step1自查 → Step2发现 → Step3备份 → Step4修复 → Step5审查 → Step6进化
        审计失败自动回滚
        """
        project = self.project_root or os.getcwd()
        engine = EvolveEngine(project, dry_run=dry_run, strong=strong)
        report = engine.run(description)

        # 记录到记忆
        status = "成功" if report.success else "失败"
        self.memory.set(f"evolve_{datetime.now().strftime('%Y%m%d%H%M')}",
                       f"{status}: {description}", category="evolve", importance=4)

        # 记录情景
        for step in report.steps:
            if step.status.value in ("ok", "fail"):
                self.memory.record_episode("evolve",
                    f"{step.name}: {step.status.value}")

        return report
