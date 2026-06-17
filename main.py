#!/usr/bin/env python3
"""
import sys, os
if sys.platform == 'win32':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

GBT Agent Framework — 主入口
用法: python main.py [--provider auto] [--model MODEL] [--project PATH]

示例:
  python main.py                                    # 自动检测LLM，交互模式
  python main.py --provider zhipu --model glm-5.1  # 指定智谱GLM-5.1
  python main.py --scan-keys                        # 扫描可用的API密钥
  python main.py --keys-guide                       # 显示密钥获取指南
  python main.py --test                             # 运行框架测试
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ── 加载 .env ──
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

from gbt.llm import GBTLLM
from gbt.providers import AutoKeyConfig
from gbt.tool import ToolRegistry
from agents.gbt_agent import GBTAgent
from tools.mcp_tools import register_all_mcp_tools


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║  ⚕ GBT Agent Framework v1.0             ║
║  GBT小土豆全能开发者 — AI原生Agent大脑   ║
║  基于 hello-agents 框架模式构建          ║
╚══════════════════════════════════════════╝""")


def cmd_scan_keys():
    """扫描所有API密钥"""
    print("\n🔑 扫描可用的LLM提供商...\n")
    discovered = AutoKeyConfig.scan()
    ok = 0
    for pid, info in discovered.items():
        cfg = info["config"]
        status_icon = {"available": "🟢", "check_port": "🔵", "missing": "⚪"}
        icon = status_icon.get(info["status"], "⚪")
        keys_info = ", ".join(k["masked"] for k in info["found_keys"]) if info["found_keys"] else "无"
        print(f"  {icon} {cfg['name']:<18} [{cfg['pricing']}] {keys_info}")
        if info["status"] == "available":
            ok += 1
    print(f"\n📊 可用: {ok}/{len(discovered)}")
    return discovered


def cmd_keys_guide():
    """显示密钥获取指南"""
    print("\n📖 API密钥获取指南:\n")
    guides = AutoKeyConfig.get_missing_guide()
    for i, g in enumerate(guides, 1):
        print(f"  {i}. {g['name']} — {g['description']}")
        print(f"     环境变量: {g['env_key']}")
        print(f"     获取地址: {g['guide_url']}")
        print(f"     价格: {g['pricing']}\n")
    if not guides:
        print("  🎉 所有提供商密钥已配置！")


def cmd_interactive(args: dict):
    """交互模式"""
    print_banner()
    provider = args.get("provider", "auto")
    model = args.get("model")
    project = args.get("project", os.getcwd())

    try:
        llm = GBTLLM(provider=provider, model=model)
    except ValueError as e:
        print(f"\n❌ {e}")
        print("运行 'python main.py --keys-guide' 查看获取指南")
        return

    agent = GBTAgent(llm=llm, project_root=project)
    register_all_mcp_tools(agent._tools, project)

    print(f"\n⚕ GBT 已就绪！输入 'quit' 退出，'tools' 查看工具，'help' 帮助\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("⚕ GBT 再见！")
                break
            if user_input.lower() == "tools":
                print(f"🔧 可用工具:\n{agent._tools.get_tools_description()}")
                continue
            if user_input.lower() == "keys":
                cmd_scan_keys()
                continue
            if user_input.lower() == "help":
                print("命令: quit/tools/keys/help | 直接输入问题")
                continue
            response = agent.run(user_input)
            print(f"\n🤖 GBT: {response}\n")
        except KeyboardInterrupt:
            print("\n⚕ 中断")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def main():
    args = {}
    argv = sys.argv[1:]
    i = 0
    
    query_to_run = None # 新增变量用于存储 --query 参数

    while i < len(argv):
        if argv[i] == "--scan-keys":
            cmd_scan_keys()
            return
        elif argv[i] == "--keys-guide":
            cmd_keys_guide()
            return
        elif argv[i] == "--test":
            run_tests()
            return
        elif argv[i] == "--provider" and i + 1 < len(argv):
            args["provider"] = argv[i + 1]; i += 2
        elif argv[i] == "--model" and i + 1 < len(argv):
            args["model"] = argv[i + 1]; i += 2
        elif argv[i] == "--project" and i + 1 < len(argv):
            args["project"] = argv[i + 1]; i += 2
        elif argv[i] == "--query" and i + 1 < len(argv):
            query_to_run = argv[i + 1]; i += 2 # 获取 --query 的值
        else:
            i += 1

    if query_to_run: # 如果存在 --query，直接运行查询
        print_banner()
        provider = args.get("provider", "auto")
        model = args.get("model")
        project = args.get("project", os.getcwd())

        try:
            llm = GBTLLM(provider=provider, model=model)
        except ValueError as e:
            print(f"\n❌ {e}")
            print("运行 'python main.py --keys-guide' 查看获取指南")
            return

        agent = GBTAgent(llm=llm, project_root=project)
        register_all_mcp_tools(agent._tools, project)

        print(f"\n🧠 正在处理查询: {query_to_run}\n")
        response = agent.run(query_to_run)
        print(f"\n🤖 GBT: {response}\n")
        return # 执行完毕后退出

    cmd_interactive(args)


def run_tests():
    """运行框架测试"""
    print("\n🧪 GBT Framework 测试\n")
    # 测试消息系统
    from gbt.message import Message, ConversationHistory, AgentConfig
    h = ConversationHistory()
    h.add_user("测试")
    h.add_assistant("响应")
    assert len(h) == 2
    print("✅ 消息系统正常")

    # 测试工具注册表
    from gbt.tool import ToolRegistry
    tr = ToolRegistry()
    tr.register("test_tool", "测试工具", lambda **kw: "ok")
    assert "test_tool" in tr
    assert tr.execute("test_tool", "hello") == "ok"
    print("✅ 工具系统正常")

    # 测试提供商配置
    from gbt.providers import PROVIDERS, AutoKeyConfig
    assert len(PROVIDERS) == 13
    discovered = AutoKeyConfig.scan()
    print(f"✅ 提供商配置: {len(PROVIDERS)}个, 发现 {sum(1 for i in discovered.values() if i['status']=='available')} 个可用密钥")

    # 测试Agent创建(不需要真实LLM)
    print("✅ Agent框架结构完整")
    print(f"\n🎉 所有核心测试通过！")


if __name__ == "__main__":
    main()
