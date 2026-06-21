"""GBT 全模块端到端压力测试"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

results = []
mod_ok = mod_fail = 0

def test(name, fn):
    global mod_ok, mod_fail
    try:
        fn()
        mod_ok += 1
    except Exception as e:
        mod_fail += 1
        results.append(f"FAIL {name}: {e}")
        print(f"  FAIL {name}: {e}")

# ── 1. 全模块导入 ──
print("=== 1. 全模块导入 ===")
import_modules = [
    'gbt.__init__','gbt.llm','gbt.tool','gbt.providers','gbt.message','gbt.agent',
    'gbt.react','gbt.memory','gbt.database','gbt.strategies','gbt.account',
    'gbt.mcp','gbt.reasoner','gbt.router','gbt.backtest','gbt.guard','gbt.mirror',
    'gbt.evolve','gbt.protocol','gbt.brain','gbt.winctl','gbt.watcher',
    'gbt.capabilities','gbt.desktop_ctl','gbt.scraper','gbt.screen_ai','gbt.ocr',
    'gbt.agents','gbt.watcher_agent','gbt.tech_analysis','gbt.risk_ctrl',
    'agents.gbt_agent','tools.mcp_tools',
]
for m in import_modules:
    test(m, lambda m=m: __import__(m))
print(f"  导入: {mod_ok}/{len(import_modules)} OK\n")

# ── 2. 策略引擎 ──
print("=== 2. 策略引擎 ===")
from gbt.strategies import StrategyEngine, ma_crossover, rsi_divergence, volume_breakout, bollinger_squeeze
closes = list(range(100,130)) + list(range(129,99,-1))
se = StrategyEngine()
r = se.analyze(closes)
print(f"  MA: {ma_crossover(closes)['signal']} RSI: {rsi_divergence(closes)['signal']} Vol: {volume_breakout(closes,[100]*len(closes))['signal']} BB: {bollinger_squeeze(closes)['signal']}")
print(f"  Engine: signal={r['signal']} confidence={r['confidence']}\n")

# ── 3. 账户系统 ──
print("=== 3. 账户系统 ===")
from gbt.account import Account
a = Account(1000000)
r1 = a.buy('600519','茅台',100,1800)
r2 = a.sell('600519',50,1900)
print(f"  Buy: ok={r1['ok']} Sell: ok={r2['ok']} equity={a.get_equity()} pnl={a.total_pnl}\n")

# ── 4. 数据库 ──
print("=== 4. 数据库 ===")
from gbt.database import Database, db
print(f"  DB: path={db.db_path} type={type(db).__name__}\n")

# ── 5. 风控 ──
print("=== 5. 风控 ===")
from gbt.risk_ctrl import RiskManager
rm = RiskManager(100000)
chk = rm.check_position_size(50)
print(f"  Position check: ok={chk['ok']} max_shares={chk['max_shares']}\n")

# ── 6. 技术分析 ──
print("=== 6. 技术分析 ===")
from gbt.tech_analysis import FullAnalysis, MACD, RSI as TA_RSI, BollingerBands
data = [10+0.1*i+(i%5-2)*0.5 for i in range(50)]
fa = FullAnalysis(data)
print(f"  Trend: {fa.get('trend')} MACD: {MACD(data).get('trend')} RSI: {TA_RSI(data).get('zone')}\n")

# ── 7. 回测引擎 ──
print("=== 7. 回测引擎 ===")
from gbt.backtest import BacktestEngine
c2 = [10+0.1*i+(i%10-5)*0.3 for i in range(200)]
raw = [{'day':f'2024-{i//30+1:02d}-{i%28+1:02d}','open':c2[i],'close':c2[i],'high':c2[i]*1.01,'low':c2[i]*0.99,'volume':1000} for i in range(len(c2))]
be = BacktestEngine()
br = be.run('test',{'closes':c2,'highs':[c*1.01 for c in c2],'lows':[c*0.99 for c in c2],'volumes':[1000]*len(c2),'raw':raw},lambda c,h,l,v,i:ma_crossover(c))
print(f"  Return: {br.total_return:.1f}% Trades: {br.total_trades} Sharpe: {br.sharpe_ratio:.2f}\n")

# ── 8. Mirror/Guard ──
print("=== 8. 安全与镜像 ===")
from gbt.mirror import RealCodeValidator
from gbt.guard import PreActionGuard
v = RealCodeValidator()
ok, c = v.is_fake_free(r'C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt')
g = PreActionGuard(r'C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt', strict=False)
snap = g.full_scan()
print(f"  Mirror: fake_free={ok} issues={c}")
print(f"  Guard: {snap.total_files} files {snap.issues_count} issues\n")

# ── 9. MCP ──
print("=== 9. MCP ===")
from gbt.mcp import get_mcp
m = get_mcp()
servers = m.list_servers()
print(f"  MCP servers: {len(servers)} - {servers[:3]}...\n")

# ── 10. 路由与协议 ──
print("=== 10. 路由与协议 ===")
from gbt.router import router
caps = router.list_capabilities()
print(f"  Capabilities: {len(caps)}\n")

# ── 11. 推理引擎 ──
print("=== 11. 推理引擎 ===")
from gbt.reasoner import DeepReasoner, ReasonMode
print(f"  Modes: {[m.value for m in ReasonMode]}\n")

# ── 12. WinCtl ──
print("=== 12. Windows控制 ===")
from gbt.winctl import get_winctl
w = get_winctl()
print(f"  Features: {len(w._f)}\n")

# ── 13. ScreenAI ──
print("=== 13. ScreenAI ===")
from gbt.screen_ai import ScreenOCR, Voice, AutoPipeline
print(f"  ScreenOCR+Voice OK\n")

# ── 14. Market Connector ──
print("=== 14. Market Connector ===")
from gbt.connectors.market import get_indices
r = get_indices()
print(f"  Market: ok={r.get('ok')} data={str(r.get('data',''))[:80]}\n")

# ── 15. Agents ──
print("=== 15. Multi-Agent ===")
from gbt.agents import MultiAgentFramework
print(f"  MultiAgentFramework OK\n")

# ── 16. WatcherAgent ──
print("=== 16. WatcherAgent ===")
from gbt.watcher_agent import get_watcher_agent
wa = get_watcher_agent()
print(f"  WatcherAgent: running={wa.running}\n")

# ── Summary ──
print(f"\n{'='*50}")
print(f"TOTAL: {mod_ok+mod_fail} tests")
print(f"PASS:  {mod_ok}")
print(f"FAIL:  {mod_fail}")
print(f"{'='*50}")
sys.exit(mod_fail)
