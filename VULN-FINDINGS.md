# Scan Report v3

**Time**:2026-06-21T17:46:20.772Z
**Deep**:N

## Summary
|Level|Count|
|---|---|
|critical|1|
|medium|6|
|low|5|
|info|1|
|Total|**13**|

## Findings
- **[MEDIUM]** desktop\app.py:209 — 硬编码IP
- **[MEDIUM]** desktop\app.py:902 — 硬编码IP
- **[MEDIUM]** gbt\agents.py:660 — 硬编码IP
- **[MEDIUM]** gbt\connectors\network.py:16 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:175 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:476 — 硬编码IP
- **[LOW]** desktop\app.py:93 — console残留
- **[LOW]** gbt\connectors\registry.py:37 — 废弃API
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
- **[LOW]** _w.js:1 — console残留
- **[CRITICAL]** gbt\evolve.py:80 — eval()注入
- **[INFO]** _w.js:1 — 循环同步IO
