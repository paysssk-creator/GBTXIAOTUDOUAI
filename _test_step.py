"""Step-by-step capability tester — GBT v1.5.1"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASSED = 0; FAILED = 0

def test_one(label, imp, chk=None):
    global PASSED, FAILED
    print(f"\n{'='*50}\nTEST: {label}\n{'='*50}")
    try:
        exec(imp)
        print(f"  IMPORT: OK")
        if chk: exec(chk); print(f"  VERIFY: OK")
        PASSED += 1; return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()
        FAILED += 1; return False

TESTS = [
    ("gbt.__init__", "import gbt", "assert gbt.__version__=='1.5.0';print(f'  v{gbt.__version__}, {len(gbt.__all__)} exports')"),
    ("gbt.llm", "import gbt.llm", "assert hasattr(gbt.llm,'GBTLLM');print(f'  GBTLLM OK')"),
    ("gbt.providers", "import gbt.providers", "assert hasattr(gbt.providers,'PROVIDERS');print(f'  providers OK')"),
    ("gbt.router", "import gbt.router", "assert hasattr(gbt.router,'SmartRouter');print(f'  SmartRouter OK')"),
    ("gbt.reasoner", "import gbt.reasoner", "assert hasattr(gbt.reasoner,'DeepReasoner');print(f'  DeepReasoner OK')"),
    ("gbt.protocol", "import gbt.protocol", "assert hasattr(gbt.protocol,'ExecutionProtocol');print(f'  ExecutionProtocol OK')"),
    ("gbt.message", "import gbt.message", "m=gbt.message.Message(content='hi',role='user');print(f'  Message: {m.content}')"),
    ("gbt.tool", "import gbt.tool", "t=gbt.tool.Tool(name='t',func=lambda x:x,description='x');print(f'  Tool: {t.name}')"),
    ("gbt.winctl", "import gbt.winctl", "assert hasattr(gbt.winctl,'WindowsController');print('  WindowsController OK')"),
    ("gbt.desktop_ctl", "import gbt.desktop_ctl", "assert hasattr(gbt.desktop_ctl,'DesktopController');print('  DesktopController OK')"),
    ("gbt.desktop_app", "import gbt.desktop_app", "assert hasattr(gbt.desktop_app,'GBTWorkstation');print('  GBTWorkstation OK')"),
    ("gbt.trader", "import gbt.trader", "assert hasattr(gbt.trader,'AShareTrader');print('  AShareTrader OK')"),
    ("gbt.strategies", "import gbt.strategies", "assert hasattr(gbt.strategies,'StrategyEngine');print('  StrategyEngine OK')"),
    ("gbt.tech_analysis", "import gbt.tech_analysis", "assert hasattr(gbt.tech_analysis,'FullAnalysis');print('  FullAnalysis OK')"),
    ("gbt.scraper", "import gbt.scraper", "assert hasattr(gbt.scraper,'PrecisionScraper');print('  PrecisionScraper OK')"),
    ("gbt.backtest", "import gbt.backtest", "assert hasattr(gbt.backtest,'BacktestEngine');print('  BacktestEngine OK')"),
    ("gbt.risk_ctrl", "import gbt.risk_ctrl", "assert hasattr(gbt.risk_ctrl,'RiskManager');print('  RiskManager OK')"),
    ("gbt.agent", "import gbt.agent", "assert hasattr(gbt.agent,'SimpleAgent');print('  SimpleAgent OK')"),
    ("gbt.agents", "import gbt.agents", "assert hasattr(gbt.agents,'get_framework');print('  get_framework OK')"),
    ("gbt.react", "import gbt.react", "assert hasattr(gbt.react,'ReActAgent');print('  ReActAgent OK')"),
    ("gbt.autopilot", "import gbt.autopilot", "assert hasattr(gbt.autopilot,'Autopilot');print('  Autopilot OK')"),
    ("gbt.brain", "import gbt.brain", "assert hasattr(gbt.brain,'AutonomousBrain');print('  AutonomousBrain OK')"),
    ("gbt.memory", "import gbt.memory", "assert hasattr(gbt.memory,'MemoryManager');print('  MemoryManager OK')"),
    ("gbt.knowledge_base", "import gbt.knowledge_base", "kb=gbt.knowledge_base.get_system_prompt();print(f'  KB len={len(kb)}')"),
    ("gbt.evolve", "import gbt.evolve", "assert hasattr(gbt.evolve,'EvolveEngine');print('  EvolveEngine OK')"),
    ("gbt.guard", "import gbt.guard", "assert hasattr(gbt.guard,'PreActionGuard');print('  PreActionGuard OK')"),
    ("gbt.mirror", "import gbt.mirror", "assert hasattr(gbt.mirror,'MirrorSpace');print('  MirrorSpace OK')"),
    ("gbt.mcp", "import gbt.mcp", "assert hasattr(gbt.mcp,'UniversalMCP');print('  UniversalMCP OK')"),
    ("gbt.database", "import gbt.database", "assert hasattr(gbt.database,'Database');print('  Database OK')"),
    ("gbt.keydb", "import gbt.keydb", "assert hasattr(gbt.keydb,'KeyDB');print('  KeyDB OK')"),
    ("gbt.cloud_kv", "import gbt.cloud_kv", "assert hasattr(gbt.cloud_kv,'CloudKV');print('  CloudKV OK')"),
    ("gbt.paper_account", "import gbt.paper_account", "assert hasattr(gbt.paper_account,'get_status');print('  get_status OK')"),
    ("gbt.account", "import gbt.account", "assert hasattr(gbt.account,'Account');print('  Account OK')"),
    ("gbt.capabilities", "import gbt.capabilities", "assert hasattr(gbt.capabilities,'Capability') and hasattr(gbt.capabilities,'register_all');print('  Capability + register_all OK')"),
    ("gbt.ocr", "import gbt.ocr", "assert hasattr(gbt.ocr,'screenshot_to_text');print('  screenshot_to_text OK')"),
    ("gbt.screen_ai", "import gbt.screen_ai", "assert hasattr(gbt.screen_ai,'AutoPipeline');print('  AutoPipeline OK')"),
    ("gbt.llm_metrics", "import gbt.llm_metrics", "assert hasattr(gbt.llm_metrics,'LLMMetrics');print('  LLMMetrics OK')"),
    ("gbt.setup_glm4v", "import gbt.setup_glm4v", "assert hasattr(gbt.setup_glm4v,'test_glm4v_vision');print('  test_glm4v_vision OK')"),
    ("gbt.watcher", "import gbt.watcher", "assert hasattr(gbt.watcher,'NightWatcher');print('  NightWatcher OK')"),
    ("gbt.watcher_agent", "import gbt.watcher_agent", "assert hasattr(gbt.watcher_agent,'WatcherAgent');print('  WatcherAgent OK')"),
    ("gbt.gcc.ai_trader", "import gbt.gcc.ai_trader", "assert hasattr(gbt.gcc.ai_trader,'AITrader');print('  AITrader OK')"),
    ("gbt.ai_operator", "import gbt.ai_operator", "assert hasattr(gbt.ai_operator,'AIDeviceOperator');print('  AIDeviceOperator OK')"),
    ("gbt.web_api", "import gbt.web_api", "assert hasattr(gbt.web_api,'app');print('  Flask app OK')"),
]

if __name__ == "__main__":
    tgt = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if tgt == 0:
        for n,i,c in TESTS: test_one(n,i,c)
    elif 1 <= tgt <= len(TESTS):
        n,i,c = TESTS[tgt-1]; test_one(n,i,c)
    else:
        grps = {1:(0,8),2:(8,11),3:(11,17),4:(17,22),5:(22,28),6:(28,33),7:(33,38),8:(38,41)}
        if tgt in grps:
            s,e = grps[tgt]
            for n,i,c in TESTS[s:e]: test_one(n,i,c)
        else:
            print(f"Unknown target: {tgt}")
    print(f"\n{'#'*50}\n# {PASSED} PASS | {FAILED} FAIL | {PASSED+FAILED} TOTAL\n{'#'*50}")
    if FAILED: sys.exit(1)
