# Scan Report v3

**Time**:2026-06-21T17:41:15.548Z
**Deep**:Y

## Summary
|Level|Count|
|---|---|
|critical|1|
|medium|101|
|low|5|
|info|1|
|Total|**108**|

## Findings
- **[MEDIUM]** agents\gbt_agent.py:107 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:175 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:181 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:182 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:207 — return后死代码
- **[MEDIUM]** desktop\app.py:209 — 硬编码IP
- **[MEDIUM]** desktop\app.py:902 — 硬编码IP
- **[MEDIUM]** desktop\app.py:446 — return后死代码
- **[MEDIUM]** desktop\app.py:460 — return后死代码
- **[MEDIUM]** desktop\app.py:876 — return后死代码
- **[MEDIUM]** desktop\app.py:1012 — return后死代码
- **[MEDIUM]** desktop\app.py:1023 — return后死代码
- **[MEDIUM]** desktop\app.py:1031 — return后死代码
- **[MEDIUM]** desktop\app.py:1127 — return后死代码
- **[MEDIUM]** desktop\app.py:1152 — return后死代码
- **[MEDIUM]** desktop\app.py:1195 — return后死代码
- **[MEDIUM]** desktop\app.py:1220 — return后死代码
- **[MEDIUM]** desktop\app.py:1229 — return后死代码
- **[MEDIUM]** desktop\app.py:1240 — return后死代码
- **[MEDIUM]** desktop\app.py:1254 — return后死代码
- **[MEDIUM]** desktop\app.py:1267 — return后死代码
- **[MEDIUM]** desktop\app.py:1270 — return后死代码
- **[MEDIUM]** gbt\account.py:42 — return后死代码
- **[MEDIUM]** gbt\agent.py:55 — return后死代码
- **[MEDIUM]** gbt\agent.py:58 — return后死代码
- **[MEDIUM]** gbt\agents.py:660 — 硬编码IP
- **[MEDIUM]** gbt\agents.py:281 — return后死代码
- **[MEDIUM]** gbt\agents.py:374 — return后死代码
- **[MEDIUM]** gbt\agents.py:390 — return后死代码
- **[MEDIUM]** gbt\agents.py:399 — return后死代码
- **[MEDIUM]** gbt\agents.py:406 — return后死代码
- **[MEDIUM]** gbt\agents.py:594 — return后死代码
- **[MEDIUM]** gbt\agents.py:595 — return后死代码
- **[MEDIUM]** gbt\agents.py:841 — return后死代码
- **[MEDIUM]** gbt\brain.py:87 — return后死代码
- **[MEDIUM]** gbt\brain.py:539 — return后死代码
- **[MEDIUM]** gbt\brain.py:545 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:47 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:61 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:89 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:92 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:134 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:165 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:297 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:298 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:330 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:356 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:388 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:465 — return后死代码
- **[MEDIUM]** gbt\connectors\github.py:47 — return后死代码
- **[MEDIUM]** gbt\connectors\github.py:81 — return后死代码
- **[MEDIUM]** gbt\connectors\network.py:16 — 硬编码IP
- **[MEDIUM]** gbt\connectors\registry.py:177 — return后死代码
- **[MEDIUM]** gbt\connectors\registry.py:196 — return后死代码
- **[MEDIUM]** gbt\database.py:350 — return后死代码
- **[MEDIUM]** gbt\database.py:407 — return后死代码
- **[MEDIUM]** gbt\database.py:440 — return后死代码
- **[MEDIUM]** gbt\evolve.py:506 — return后死代码
- **[MEDIUM]** gbt\gcc\ai_trader.py:120 — return后死代码
- **[MEDIUM]** gbt\gcc\ai_trader.py:121 — return后死代码
- **[MEDIUM]** gbt\gcc\ai_trader.py:132 — return后死代码
- **[MEDIUM]** gbt\gcc\gcc_runner.py:267 — return后死代码
- **[MEDIUM]** gbt\gcc\gcc_runner.py:278 — return后死代码
- **[MEDIUM]** gbt\gcc\gcc_runner.py:283 — return后死代码
- **[MEDIUM]** gbt\gcc\screenshot_reasoner.py:55 — return后死代码
- **[MEDIUM]** gbt\gcc\self_reflection.py:77 — return后死代码
- **[MEDIUM]** gbt\gcc\self_reflection.py:95 — return后死代码
- **[MEDIUM]** gbt\gcc\skill_curation.py:43 — return后死代码
- **[MEDIUM]** gbt\gcc\skill_curation.py:367 — return后死代码
- **[MEDIUM]** gbt\gcc\skill_curation.py:407 — return后死代码
- **[MEDIUM]** gbt\gcc\skill_curation.py:438 — return后死代码
- **[MEDIUM]** gbt\guard.py:148 — return后死代码
- **[MEDIUM]** gbt\llm.py:103 — return后死代码
- **[MEDIUM]** gbt\mcp.py:104 — return后死代码
- **[MEDIUM]** gbt\memory.py:81 — return后死代码
- **[MEDIUM]** gbt\memory.py:105 — return后死代码
- **[MEDIUM]** gbt\protocol.py:76 — return后死代码
- **[MEDIUM]** gbt\protocol.py:178 — return后死代码
- **[MEDIUM]** gbt\protocol.py:184 — return后死代码
- **[MEDIUM]** gbt\protocol.py:190 — return后死代码
- **[MEDIUM]** gbt\reasoner.py:348 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:29 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:42 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:55 — return后死代码
- **[MEDIUM]** gbt\scraper.py:208 — return后死代码
- **[MEDIUM]** gbt\strategies.py:79 — return后死代码
- **[MEDIUM]** gbt\tech_analysis.py:16 — return后死代码
- **[MEDIUM]** gbt\tech_analysis.py:23 — return后死代码
- **[MEDIUM]** gbt\tool.py:58 — return后死代码
- **[MEDIUM]** gbt\tool.py:90 — return后死代码
- **[MEDIUM]** gbt\trader.py:434 — return后死代码
- **[MEDIUM]** gbt\trader.py:663 — return后死代码
- **[MEDIUM]** gbt\trader.py:795 — return后死代码
- **[MEDIUM]** gbt\watcher.py:175 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:476 — 硬编码IP
- **[MEDIUM]** gbt\watcher_agent.py:594 — return后死代码
- **[MEDIUM]** gbt\winctl.py:79 — return后死代码
- **[MEDIUM]** gbt\winctl.py:93 — return后死代码
- **[MEDIUM]** gbt\winctl.py:272 — return后死代码
- **[MEDIUM]** start_demo.py:25 — return后死代码
- **[MEDIUM]** tools\mcp_tools.py:15 — return后死代码
- **[LOW]** desktop\app.py:93 — console残留
- **[LOW]** gbt\connectors\registry.py:37 — 废弃API
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
- **[LOW]** _w.js:1 — console残留
- **[CRITICAL]** gbt\evolve.py:80 — eval()注入
- **[INFO]** _w.js:1 — 循环同步IO
