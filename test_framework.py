"""Quick framework validation test."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

errors = []

# 1. Test providers
try:
    from gbt.providers import PROVIDERS, AutoKeyConfig
    assert len(PROVIDERS) >= 13, f"Expected >=13 providers, got {len(PROVIDERS)}"
    discovered = AutoKeyConfig.scan()
    available = sum(1 for v in discovered.values() if v["status"] == "available")
    print(f"  [OK] Providers: {len(PROVIDERS)} total, {available} available")
except Exception as e:
    errors.append(f"Providers: {e}")

# 2. Test message system
try:
    from gbt.message import Message, ConversationHistory, AgentConfig
    h = ConversationHistory()
    h.add_user("hello")
    h.add_assistant("hi")
    assert len(h) == 2, "History should have 2 messages"
    print(f"  [OK] Message: {len(h)} messages")
except Exception as e:
    errors.append(f"Message: {e}")

# 3. Test tool registry
try:
    from gbt.tool import ToolRegistry
    tr = ToolRegistry()
    tr.register("test", "test tool", lambda **kw: "ok")
    assert "test" in tr
    assert tr.execute("test", "hello") == "ok"
    print(f"  [OK] ToolRegistry: {len(tr)} tool(s)")
except Exception as e:
    errors.append(f"ToolRegistry: {e}")

# 4. Test LLM abstraction (without real API key)
try:
    from gbt.llm import GBTLLM
    print(f"  [OK] LLM module loads")
except Exception as e:
    errors.append(f"LLM: {e}")

# 5. Test memory
try:
    from gbt.memory import MemoryManager
    mm = MemoryManager()
    mm.set("test_key", "test_value", importance=3)
    val = mm.get("test_key")
    assert val == "test_value"
    stats = mm.stats()
    print(f"  [OK] Memory: {stats}")
except Exception as e:
    errors.append(f"Memory: {e}")

# 6. Test guard
try:
    from gbt.guard import scan_all
    snap = scan_all(os.path.dirname(__file__))
    print(f"  [OK] Guard scan: {snap.total_files} files, {snap.issues_count} issues")
except Exception as e:
    errors.append(f"Guard: {e}")

# 7. Test mirror/validator
try:
    from gbt.mirror import scan_fakes, RealCodeValidator
    issues = scan_fakes(os.path.dirname(__file__))
    print(f"  [OK] Mirror scan: {len(issues)} fake issues found")
except Exception as e:
    errors.append(f"Mirror: {e}")

# 8. Test evolve engine (dry run)
try:
    from gbt.evolve import run_evolve
    print(f"  [OK] Evolve module loads")
except Exception as e:
    errors.append(f"Evolve: {e}")

# 9. Test MCP
try:
    from gbt.mcp import UniversalMCP, get_mcp
    mcp = get_mcp()
    servers = mcp.list_servers()
    print(f"  [OK] MCP: {len(servers)} servers")
except Exception as e:
    errors.append(f"MCP: {e}")

# 10. Test reasoner (no LLM needed)
try:
    from gbt.reasoner import ReasonMode, DeepReasoner
    modes = [m.value for m in ReasonMode]
    print(f"  [OK] Reasoner: {len(modes)} modes - {', '.join(modes)}")
except Exception as e:
    errors.append(f"Reasoner: {e}")

# 11. Test winctl
try:
    from gbt.winctl import WindowsController, WinFeature, get_winctl
    features = [f.value for f in WinFeature]
    print(f"  [OK] WinCtl: {len(features)} features - {', '.join(features)}")
except Exception as e:
    errors.append(f"WinCtl: {e}")

# 12. Test OCR
try:
    from gbt.ocr import ImageToText
    print(f"  [OK] OCR module loads")
except Exception as e:
    errors.append(f"OCR: {e}")

# 13. Test ReAct
try:
    from gbt.react import ReActAgent
    print(f"  [OK] ReAct module loads")
except Exception as e:
    errors.append(f"ReAct: {e}")

# 14. Test Agent
try:
    from gbt.agent import SimpleAgent, AgentConfig
    config = AgentConfig(name="test")
    print(f"  [OK] Agent base: {config.name}")
except Exception as e:
    errors.append(f"Agent: {e}")

# 15. Test GBTAgent import
try:
    from agents.gbt_agent import GBTAgent
    print(f"  [OK] GBTAgent importable")
except Exception as e:
    errors.append(f"GBTAgent: {e}")

# 16. Test MCP tools
try:
    from tools.mcp_tools import register_all_mcp_tools
    print(f"  [OK] MCP tools importable")
except Exception as e:
    errors.append(f"MCP tools: {e}")

# Summary
print(f"\n{'='*50}")
if errors:
    print(f"FAILED: {len(errors)} error(s)")
    for e in errors:
        print(f"  X {e}")
    sys.exit(1)
else:
    print(f"ALL TESTS PASSED - 16/16 modules OK")
    print(f"{'='*50}")
