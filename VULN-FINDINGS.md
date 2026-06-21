# Scan Report v3

**Time**:2026-06-21T10:50:06.229Z
**Deep**:N

## Summary
|Level|Count|
|---|---|
|critical|1|
|medium|8|
|low|4|
|info|1|
|Total|**14**|

## Findings
- **[MEDIUM]** desktop\app.py:193 — 硬编码IP
- **[MEDIUM]** desktop\app.py:194 — 硬编码IP
- **[MEDIUM]** desktop\app.py:868 — 硬编码IP
- **[MEDIUM]** gbt\agents.py:660 — 硬编码IP
- **[MEDIUM]** gbt\connectors\network.py:17 — 硬编码IP
- **[MEDIUM]** gbt\connectors\network.py:19 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:169 — 硬编码IP
- **[MEDIUM]** gbt\watcher.py:469 — 硬编码IP
- **[LOW]** desktop\app.py:77 — console残留
- **[LOW]** gbt\mirror.py:55 — 待办标记
- **[LOW]** gbt\mirror.py:56 — 待办标记
- **[LOW]** _w.js:1 — console残留
- **[CRITICAL]** gbt\evolve.py:80 — eval()注入
- **[INFO]** _w.js:1 — 循环同步IO
