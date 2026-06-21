# Scan Report v3

**Time**:2026-06-21T18:47:51.605Z
**Deep**:N

## Summary
|Level|Count|
|---|---|
|critical|1|
|medium|1|
|low|5|
|info|1|
|Total|**8**|

## Findings
- **[MEDIUM]** gbt\__init__.py:28 — 硬编码IP
- **[LOW]** desktop\app.py:94 — console残留
- **[LOW]** gbt\connectors\registry.py:37 — 废弃API
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
- **[LOW]** _w.js:1 — console残留
- **[CRITICAL]** gbt\evolve.py:80 — eval()注入
- **[INFO]** _w.js:1 — 循环同步IO
