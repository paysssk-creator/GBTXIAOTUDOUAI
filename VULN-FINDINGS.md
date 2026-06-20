# Scan Report v3

**Time**:2026-06-20T14:31:24.283Z
**Deep**:Y

## Summary
|Level|Count|
|---|---|
|medium|82|
|low|3|
|Total|**85**|

## Findings
- **[MEDIUM]** agents\gbt_agent.py:107 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:175 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:181 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:182 — return后死代码
- **[MEDIUM]** agents\gbt_agent.py:207 — return后死代码
- **[MEDIUM]** desktop\app.py:185 — 硬编码IP
- **[MEDIUM]** desktop\app.py:186 — 硬编码IP
- **[MEDIUM]** desktop\app.py:765 — 硬编码IP
- **[MEDIUM]** desktop\app.py:234 — return后死代码
- **[MEDIUM]** desktop\app.py:262 — return后死代码
- **[MEDIUM]** desktop\app.py:276 — return后死代码
- **[MEDIUM]** desktop\app.py:739 — return后死代码
- **[MEDIUM]** desktop\app.py:859 — return后死代码
- **[MEDIUM]** desktop\app.py:870 — return后死代码
- **[MEDIUM]** desktop\app.py:878 — return后死代码
- **[MEDIUM]** desktop\app.py:974 — return后死代码
- **[MEDIUM]** desktop\app.py:999 — return后死代码
- **[MEDIUM]** desktop\app.py:1042 — return后死代码
- **[MEDIUM]** desktop\app.py:1067 — return后死代码
- **[MEDIUM]** desktop\app.py:1076 — return后死代码
- **[MEDIUM]** desktop\app.py:1087 — return后死代码
- **[MEDIUM]** desktop\app.py:1101 — return后死代码
- **[MEDIUM]** desktop\app.py:1114 — return后死代码
- **[MEDIUM]** desktop\app.py:1117 — return后死代码
- **[MEDIUM]** gbt\account.py:42 — return后死代码
- **[MEDIUM]** gbt\agent.py:55 — return后死代码
- **[MEDIUM]** gbt\agent.py:58 — return后死代码
- **[MEDIUM]** gbt\agents.py:547 — 硬编码IP
- **[MEDIUM]** gbt\agents.py:264 — return后死代码
- **[MEDIUM]** gbt\agents.py:318 — return后死代码
- **[MEDIUM]** gbt\agents.py:334 — return后死代码
- **[MEDIUM]** gbt\agents.py:343 — return后死代码
- **[MEDIUM]** gbt\agents.py:350 — return后死代码
- **[MEDIUM]** gbt\agents.py:481 — return后死代码
- **[MEDIUM]** gbt\agents.py:482 — return后死代码
- **[MEDIUM]** gbt\agents.py:629 — return后死代码
- **[MEDIUM]** gbt\brain.py:69 — return后死代码
- **[MEDIUM]** gbt\brain.py:488 — return后死代码
- **[MEDIUM]** gbt\brain.py:494 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:47 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:61 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:89 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:92 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:133 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:164 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:295 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:296 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:327 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:353 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:385 — return后死代码
- **[MEDIUM]** gbt\capabilities.py:461 — return后死代码
- **[MEDIUM]** gbt\connectors\registry.py:177 — return后死代码
- **[MEDIUM]** gbt\connectors\registry.py:189 — return后死代码
- **[MEDIUM]** gbt\database.py:350 — return后死代码
- **[MEDIUM]** gbt\database.py:407 — return后死代码
- **[MEDIUM]** gbt\database.py:439 — return后死代码
- **[MEDIUM]** gbt\guard.py:147 — return后死代码
- **[MEDIUM]** gbt\llm.py:82 — return后死代码
- **[MEDIUM]** gbt\llm.py:93 — return后死代码
- **[MEDIUM]** gbt\mcp.py:72 — return后死代码
- **[MEDIUM]** gbt\memory.py:81 — return后死代码
- **[MEDIUM]** gbt\memory.py:105 — return后死代码
- **[MEDIUM]** gbt\protocol.py:74 — return后死代码
- **[MEDIUM]** gbt\protocol.py:176 — return后死代码
- **[MEDIUM]** gbt\protocol.py:182 — return后死代码
- **[MEDIUM]** gbt\protocol.py:188 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:29 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:42 — return后死代码
- **[MEDIUM]** gbt\risk_ctrl.py:55 — return后死代码
- **[MEDIUM]** gbt\strategies.py:79 — return后死代码
- **[MEDIUM]** gbt\tech_analysis.py:16 — return后死代码
- **[MEDIUM]** gbt\tech_analysis.py:23 — return后死代码
- **[MEDIUM]** gbt\tool.py:58 — return后死代码
- **[MEDIUM]** gbt\tool.py:90 — return后死代码
- **[MEDIUM]** gbt\trader.py:433 — return后死代码
- **[MEDIUM]** gbt\trader.py:635 — return后死代码
- **[MEDIUM]** gbt\trader.py:765 — return后死代码
- **[MEDIUM]** gbt\watcher.py:168 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:467 — 硬编码IP
- **[MEDIUM]** gbt\watcher_agent.py:564 — return后死代码
- **[MEDIUM]** start_demo.py:17 — return后死代码
- **[MEDIUM]** tools\mcp_tools.py:15 — return后死代码
- **[LOW]** desktop\app.py:78 — console残留
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
