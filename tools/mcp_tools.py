"""
mcp_tools.py — 万能MCP工具注册
基于 UniversalMCP — 动态调用任意MCP Server，不受限
"""

from gbt.tool import ToolRegistry
from gbt.mcp import get_mcp, call_mcp


def mcp_call(server: str, method: str = "", args: str = "") -> str:
    """通用MCP调用器 — 任意服务器"""
    result = call_mcp(server, method, args)
    if result.ok:
        return f"✅ {server}: {result.data[:2000] if result.data else '完成'}"
    return f"❌ {server}: {result.error}"


def register_all_mcp_tools(registry: ToolRegistry, project: str = ".") -> ToolRegistry:
    """注册万能MCP工具 — 自动发现所有MCP Server并注册"""
    mcp = get_mcp()
    servers = mcp.list_servers()

    # 1. 注册万能MCP调用工具
    registry.register("mcp", "万能MCP调用: 调用任意MCP服务器 server method args",
        lambda **kw: mcp_call(kw.get("server",""), kw.get("method",""), kw.get("args","")),
        {"server": "服务器名(如scanner/audit/mirror-deploy)", "method": "方法", "args": "参数"})

    registry.register("mcp_list", "列出所有MCP服务器",
        lambda **kw: mcp.describe(),
        {})

    registry.register("mcp_search", "搜索MCP服务器 keyword",
        lambda **kw: str(mcp.search(kw.get("keyword",""))),
        {"keyword": "搜索关键词"})

    registry.register("mcp_health", "MCP服务器健康检查",
        lambda **kw: str(mcp.health()),
        {})

    registry.register("mcp_pipeline", "MCP管道调用 server1,method1,args1|server2,method2,args2",
        lambda **kw: _pipeline(kw.get("steps","")),
        {"steps": "管道步骤: srv1,m1,a1|srv2,m2,a2"})

    # 2. 为核心MCP Server注册快捷工具
    core_servers = [
        ("scanner", "代码安全扫描", "scanner"),
        ("audit", "项目健康审计", "audit", "--strict"),
        ("evolve", "6步自进化闭环", "self-evolve"),
        ("auto_fix", "一键自动修复", "auto-fix", "--confirm"),
        ("mirror_deploy", "镜像空间部署", "mirror-deploy", "--deploy"),
        ("stress_test", "压力测试", "stress-test"),
        ("bounty", "漏洞赏金扫描", "bounty-hunter"),
        ("deepseek", "DeepSeek深度分析", "deepseek-analyzer"),
    ]

    for item in core_servers:
        name, desc, srv_command, *extra_args = item # 允许额外参数
        method = ""
        args = " ".join(extra_args) # 将额外参数合并为字符串

        registry.register(name, desc,
            lambda **kw: mcp_call(srv_command, method, args),
            {"query": "可选查询参数"})

    print(f"🔧 万能MCP: {len(servers)}个服务器, {len(core_servers)+5}个工具")
    return registry


def _pipeline(steps_str: str) -> str:
    """执行MCP管道"""
    steps = []
    for step in steps_str.split("|"):
        parts = step.strip().split(",")
        if len(parts) >= 2:
            steps.append((parts[0].strip(), parts[1].strip(),
                         parts[2].strip() if len(parts) > 2 else ""))
    mcp = get_mcp()
    results = mcp.pipeline(steps)
    return "\n".join(f"{'✅' if r.ok else '❌'} {r.server}: {r.data[:200] if r.data else r.error}" for r in results)

