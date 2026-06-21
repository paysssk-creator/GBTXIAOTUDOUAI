# Scan Report v3

**Time**:2026-06-21T13:06:20.316Z
**Deep**:N

## Summary
|Level|Count|
|---|---|
|critical|1|
|medium|8|
|low|5|
|info|1|
|Total|**15**|

## Findings
- **[MEDIUM]** desktop\app.py:209 — 硬编码IP
- **[MEDIUM]** desktop\app.py:210 — 硬编码IP
- **[MEDIUM]** desktop\app.py:901 — 硬编码IP
- **[MEDIUM]** gbt\agents.py:660 — 硬编码IP
- **[MEDIUM]** gbt\connectors\network.py:17 — 硬编码IP
- **[MEDIUM]** gbt\connectors\network.py:19 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:175 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:475 — 硬编码IP
- **[LOW]** desktop\app.py:93 — console残留
- **[LOW]** gbt\connectors\registry.py:37 — 废弃API
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
- **[LOW]** _w.js:1 — console残留
- **[CRITICAL]** gbt\evolve.py:80 — eval()注入
- **[INFO]** _w.js:1 — 循环同步IO
