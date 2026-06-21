# 🏴 Bug Bounty Report — GBT-MQNUTG9A

**猎人**: GBT小土豆全能开发者  
**目标**: C:\Users\ADMIN\GBTXIAOTUDOUAI  
**时间**: 2026-06-21T14:00:35.471Z  

## 摘要
| 严重度 | 数量 |
|--------|------|
| 🔴 High | 0 |
| 🟠 Medium | 103 |

**预估赏金范围**: $100-$500

## 发现细节


### 1. [MEDIUM] undefined
- **文件**: `agents\gbt_agent.py:107`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return ("GBT全能开发者工具:\n"
  ```
- **修复建议**: 请根据上下文手动审查


### 2. [MEDIUM] undefined
- **文件**: `agents\gbt_agent.py:175`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  reports = mirror_run(project, fix_in_mirror)
  ```
- **修复建议**: 请根据上下文手动审查


### 3. [MEDIUM] undefined
- **文件**: `agents\gbt_agent.py:181`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"❌ 仍有{count}个虚假代码，禁止部署"
  ```
- **修复建议**: 请根据上下文手动审查


### 4. [MEDIUM] undefined
- **文件**: `agents\gbt_agent.py:182`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"未知操作: {action}"
  ```
- **修复建议**: 请根据上下文手动审查


### 5. [MEDIUM] undefined
- **文件**: `agents\gbt_agent.py:207`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  kw = {}
  ```
- **修复建议**: 请根据上下文手动审查


### 6. [MEDIUM] undefined
- **文件**: `desktop\app.py:209`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  cmds={"ping":["ping","-n","4","8.8.8.8"],"dns":["nslookup","google.com"],
  ```
- **修复建议**: 请根据上下文手动审查


### 7. [MEDIUM] undefined
- **文件**: `desktop\app.py:210`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  "tracert":["tracert","-h","5","8.8.8.8"],"netstat":["netstat","-an"]}
  ```
- **修复建议**: 请根据上下文手动审查


### 8. [MEDIUM] undefined
- **文件**: `desktop\app.py:901`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  p = subprocess.run(["ping", "-n", "3", "8.8.8.8"] if platform.system()=="Windows" else ["ping","-c","3","8.8.8.8"],
  ```
- **修复建议**: 请根据上下文手动审查


### 9. [MEDIUM] undefined
- **文件**: `desktop\app.py:445`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "",204
  ```
- **修复建议**: 请根据上下文手动审查


### 10. [MEDIUM] undefined
- **文件**: `desktop\app.py:459`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "", 204
  ```
- **修复建议**: 请根据上下文手动审查


### 11. [MEDIUM] undefined
- **文件**: `desktop\app.py:875`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  import urllib.request, urllib.parse
  ```
- **修复建议**: 请根据上下文手动审查


### 12. [MEDIUM] undefined
- **文件**: `desktop\app.py:1010`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify({"error": "多Agent框架未初始化"}), 503
  ```
- **修复建议**: 请根据上下文手动审查


### 13. [MEDIUM] undefined
- **文件**: `desktop\app.py:1021`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify({"error": "多Agent框架未初始化"}), 503
  ```
- **修复建议**: 请根据上下文手动审查


### 14. [MEDIUM] undefined
- **文件**: `desktop\app.py:1029`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify({"error": "多Agent框架未初始化"}), 503
  ```
- **修复建议**: 请根据上下文手动审查


### 15. [MEDIUM] undefined
- **文件**: `desktop\app.py:1125`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  sig = trader.analyze_with_ai(code, quotes[code])
  ```
- **修复建议**: 请根据上下文手动审查


### 16. [MEDIUM] undefined
- **文件**: `desktop\app.py:1150`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify(trader.execute_trade(code, action, shares, price))
  ```
- **修复建议**: 请根据上下文手动审查


### 17. [MEDIUM] undefined
- **文件**: `desktop\app.py:1193`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify(trader.get_status())
  ```
- **修复建议**: 请根据上下文手动审查


### 18. [MEDIUM] undefined
- **文件**: `desktop\app.py:1218`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify({"ok": False, "error": "会话不存在"})
  ```
- **修复建议**: 请根据上下文手动审查


### 19. [MEDIUM] undefined
- **文件**: `desktop\app.py:1227`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify(trader.open_stock_page(code))
  ```
- **修复建议**: 请根据上下文手动审查


### 20. [MEDIUM] undefined
- **文件**: `desktop\app.py:1238`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return jsonify(trader.fetch_kline(code, scale, datalen))
  ```
- **修复建议**: 请根据上下文手动审查


### 21. [MEDIUM] undefined
- **文件**: `desktop\app.py:1252`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  result = se.analyze(kline.get("closes", []), kline.get("highs"),
  ```
- **修复建议**: 请根据上下文手动审查


### 22. [MEDIUM] undefined
- **文件**: `desktop\app.py:1265`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  quote = trader.fetch_quote([code])
  ```
- **修复建议**: 请根据上下文手动审查


### 23. [MEDIUM] undefined
- **文件**: `desktop\app.py:1268`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  q = quote[code]
  ```
- **修复建议**: 请根据上下文手动审查


### 24. [MEDIUM] undefined
- **文件**: `gbt\account.py:42`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  pos = self.positions[code]
  ```
- **修复建议**: 请根据上下文手动审查


### 25. [MEDIUM] undefined
- **文件**: `gbt\agent.py:55`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  tools_desc = self.tool_registry.get_tools_description()
  ```
- **修复建议**: 请根据上下文手动审查


### 26. [MEDIUM] undefined
- **文件**: `gbt\agent.py:58`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return (base + "\n\n## 可用工具\n"
  ```
- **修复建议**: 请根据上下文手动审查


### 27. [MEDIUM] undefined
- **文件**: `gbt\agents.py:660`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  cmds={"ping":["ping","-n","4","8.8.8.8"],"dns":["nslookup","google.com"],"tracert":["tracert","-h","5","8.8.8.8"],"netst
  ```
- **修复建议**: 请根据上下文手动审查


### 28. [MEDIUM] undefined
- **文件**: `gbt\agents.py:281`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  subprocess.run(["nircmd","changesysvolume","2000"],capture_output=True,timeout=3
  ```
- **修复建议**: 请根据上下文手动审查


### 29. [MEDIUM] undefined
- **文件**: `gbt\agents.py:374`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  code = m.group(1)
  ```
- **修复建议**: 请根据上下文手动审查


### 30. [MEDIUM] undefined
- **文件**: `gbt\agents.py:390`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"{name}({code}): 数据解析异常"
  ```
- **修复建议**: 请根据上下文手动审查


### 31. [MEDIUM] undefined
- **文件**: `gbt\agents.py:399`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "交易引擎未就绪"
  ```
- **修复建议**: 请根据上下文手动审查


### 32. [MEDIUM] undefined
- **文件**: `gbt\agents.py:406`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "交易引擎未就绪"
  ```
- **修复建议**: 请根据上下文手动审查


### 33. [MEDIUM] undefined
- **文件**: `gbt\agents.py:594`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"文件不存在: {fpath}"
  ```
- **修复建议**: 请根据上下文手动审查


### 34. [MEDIUM] undefined
- **文件**: `gbt\agents.py:595`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "请指定要读取的文件路径"
  ```
- **修复建议**: 请根据上下文手动审查


### 35. [MEDIUM] undefined
- **文件**: `gbt\agents.py:840`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  ws = self.watcher.get_status()
  ```
- **修复建议**: 请根据上下文手动审查


### 36. [MEDIUM] undefined
- **文件**: `gbt\brain.py:87`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  self.running = True
  ```
- **修复建议**: 请根据上下文手动审查


### 37. [MEDIUM] undefined
- **文件**: `gbt\brain.py:539`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return self.router.route(text)
  ```
- **修复建议**: 请根据上下文手动审查


### 38. [MEDIUM] undefined
- **文件**: `gbt\brain.py:545`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  ctx = self.router.get_capability_context()
  ```
- **修复建议**: 请根据上下文手动审查


### 39. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:47`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  code = m.group(1)
  ```
- **修复建议**: 请根据上下文手动审查


### 40. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:61`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"未找到 {code} 的行情数据"
  ```
- **修复建议**: 请根据上下文手动审查


### 41. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:89`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  wl = getattr(trader, 'watchlist', {}) or {}
  ```
- **修复建议**: 请根据上下文手动审查


### 42. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:92`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  lines = ["📋 自选股:"]
  ```
- **修复建议**: 请根据上下文手动审查


### 43. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:134`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  ws = watcher.get_status()
  ```
- **修复建议**: 请根据上下文手动审查


### 44. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:165`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  code = m.group(1)
  ```
- **修复建议**: 请根据上下文手动审查


### 45. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:297`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"文件不存在: {fpath}"
  ```
- **修复建议**: 请根据上下文手动审查


### 46. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:298`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "请指定要读取的文件路径"
  ```
- **修复建议**: 请根据上下文手动审查


### 47. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:330`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "请提供要执行的代码或命令 (用 ```python ... ``` 或 执行: ...)"
  ```
- **修复建议**: 请根据上下文手动审查


### 48. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:356`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"OCR失败: {r.get('error', '未知错误')}"
  ```
- **修复建议**: 请根据上下文手动审查


### 49. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:388`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"⚠ 未检测到登录 (置信度 {r['confidence']}) | 找到: {r.get('found_keywords', [])} | 
  ```
- **修复建议**: 请根据上下文手动审查


### 50. [MEDIUM] undefined
- **文件**: `gbt\capabilities.py:465`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"⚠ 流水线: {r['phase']} — {r.get('message', r.get('error', ''))}"
  ```
- **修复建议**: 请根据上下文手动审查


### 51. [MEDIUM] undefined
- **文件**: `gbt\connectors\github.py:47`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return {"ok": False, "error": "GitHub: 未登录gh CLI，请指定owner参数"}
  ```
- **修复建议**: 请根据上下文手动审查


### 52. [MEDIUM] undefined
- **文件**: `gbt\connectors\github.py:81`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return _gh(["search", "repos", "stars:>1000", "--sort", "stars", "--limit", "10"
  ```
- **修复建议**: 请根据上下文手动审查


### 53. [MEDIUM] undefined
- **文件**: `gbt\connectors\network.py:17`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  h = {"ping": lambda: ping_host(params.get("host", "8.8.8.8"), params.get("count", 4)),
  ```
- **修复建议**: 请根据上下文手动审查


### 54. [MEDIUM] undefined
- **文件**: `gbt\connectors\network.py:19`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  "traceroute": lambda: traceroute(params.get("host", "8.8.8.8"))}.get(action)
  ```
- **修复建议**: 请根据上下文手动审查


### 55. [MEDIUM] undefined
- **文件**: `gbt\connectors\registry.py:177`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  c = self._connectors[conn_id]
  ```
- **修复建议**: 请根据上下文手动审查


### 56. [MEDIUM] undefined
- **文件**: `gbt\connectors\registry.py:196`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  c.status = "connected"
  ```
- **修复建议**: 请根据上下文手动审查


### 57. [MEDIUM] undefined
- **文件**: `gbt\database.py:350`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return c.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
  ```
- **修复建议**: 请根据上下文手动审查


### 58. [MEDIUM] undefined
- **文件**: `gbt\database.py:407`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  rows = c.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (limit,
  ```
- **修复建议**: 请根据上下文手动审查


### 59. [MEDIUM] undefined
- **文件**: `gbt\database.py:440`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return default
  ```
- **修复建议**: 请根据上下文手动审查


### 60. [MEDIUM] undefined
- **文件**: `gbt\evolve.py:506`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  size /= 1024
  ```
- **修复建议**: 请根据上下文手动审查


### 61. [MEDIUM] undefined
- **文件**: `gbt\gcc\ai_trader.py:120`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "switch_failed"
  ```
- **修复建议**: 请根据上下文手动审查


### 62. [MEDIUM] undefined
- **文件**: `gbt\gcc\ai_trader.py:121`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "ok"  # 看不出就继续, 不重复切
  ```
- **修复建议**: 请根据上下文手动审查


### 63. [MEDIUM] undefined
- **文件**: `gbt\gcc\ai_trader.py:132`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  self._last_trade_key = key
  ```
- **修复建议**: 请根据上下文手动审查


### 64. [MEDIUM] undefined
- **文件**: `gbt\gcc\gcc_runner.py:267`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return None
  ```
- **修复建议**: 请根据上下文手动审查


### 65. [MEDIUM] undefined
- **文件**: `gbt\gcc\gcc_runner.py:278`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
  ```
- **修复建议**: 请根据上下文手动审查


### 66. [MEDIUM] undefined
- **文件**: `gbt\gcc\gcc_runner.py:283`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return None
  ```
- **修复建议**: 请根据上下文手动审查


### 67. [MEDIUM] undefined
- **文件**: `gbt\gcc\screenshot_reasoner.py:55`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return {"ok": True, "raw": raw}
  ```
- **修复建议**: 请根据上下文手动审查


### 68. [MEDIUM] undefined
- **文件**: `gbt\gcc\self_reflection.py:77`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return {"success": True, "reasoning": raw[:200], "next_action": "continue"}
  ```
- **修复建议**: 请根据上下文手动审查


### 69. [MEDIUM] undefined
- **文件**: `gbt\gcc\self_reflection.py:95`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  time.sleep(1)
  ```
- **修复建议**: 请根据上下文手动审查


### 70. [MEDIUM] undefined
- **文件**: `gbt\gcc\skill_curation.py:43`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  success_rate = self.success_count / total
  ```
- **修复建议**: 请根据上下文手动审查


### 71. [MEDIUM] undefined
- **文件**: `gbt\gcc\skill_curation.py:367`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  skill = self.skills[skill_name]
  ```
- **修复建议**: 请根据上下文手动审查


### 72. [MEDIUM] undefined
- **文件**: `gbt\gcc\skill_curation.py:407`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  total_usage = sum(s.usage for s in self.skills.values())
  ```
- **修复建议**: 请根据上下文手动审查


### 73. [MEDIUM] undefined
- **文件**: `gbt\gcc\skill_curation.py:438`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return len(a & b) / len(a | b)
  ```
- **修复建议**: 请根据上下文手动审查


### 74. [MEDIUM] undefined
- **文件**: `gbt\guard.py:148`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return pre, self.post_action_check(action)
  ```
- **修复建议**: 请根据上下文手动审查


### 75. [MEDIUM] undefined
- **文件**: `gbt\llm.py:103`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return None
  ```
- **修复建议**: 请根据上下文手动审查


### 76. [MEDIUM] undefined
- **文件**: `gbt\mcp.py:72`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "\n".join(f"- **{s.name}**: {s.description}" for s in self._s.values())
  ```
- **修复建议**: 请根据上下文手动审查


### 77. [MEDIUM] undefined
- **文件**: `gbt\memory.py:81`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return None
  ```
- **修复建议**: 请根据上下文手动审查


### 78. [MEDIUM] undefined
- **文件**: `gbt\memory.py:105`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  lines = ["## 相关记忆"]
  ```
- **修复建议**: 请根据上下文手动审查


### 79. [MEDIUM] undefined
- **文件**: `gbt\protocol.py:76`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return True, "default: valid dict with data"
  ```
- **修复建议**: 请根据上下文手动审查


### 80. [MEDIUM] undefined
- **文件**: `gbt\protocol.py:178`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  missing = []
  ```
- **修复建议**: 请根据上下文手动审查


### 81. [MEDIUM] undefined
- **文件**: `gbt\protocol.py:184`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return True, f"{len(cap.requires)} deps ready"
  ```
- **修复建议**: 请根据上下文手动审查


### 82. [MEDIUM] undefined
- **文件**: `gbt\protocol.py:190`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  ok_count = sum(1 for h in self._history if h["ok"])
  ```
- **修复建议**: 请根据上下文手动审查


### 83. [MEDIUM] undefined
- **文件**: `gbt\reasoner.py:348`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  best = max(results, key=lambda x: x.confidence)
  ```
- **修复建议**: 请根据上下文手动审查


### 84. [MEDIUM] undefined
- **文件**: `gbt\risk_ctrl.py:29`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  max_shares = max(0, int(self.total_capital * self.max_single_pct / 100 / price /
  ```
- **修复建议**: 请根据上下文手动审查


### 85. [MEDIUM] undefined
- **文件**: `gbt\risk_ctrl.py:42`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  loss_pct = round((entry_price - current_price) / entry_price * 100, 2)
  ```
- **修复建议**: 请根据上下文手动审查


### 86. [MEDIUM] undefined
- **文件**: `gbt\risk_ctrl.py:55`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  gain_pct = round((current_price - entry_price) / entry_price * 100, 2)
  ```
- **修复建议**: 请根据上下文手动审查


### 87. [MEDIUM] undefined
- **文件**: `gbt\scraper.py:208`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return {"ok": False, "error": "无法获取资讯", "code": code}
  ```
- **修复建议**: 请根据上下文手动审查


### 88. [MEDIUM] undefined
- **文件**: `gbt\strategies.py:79`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return round(100 - 100 / (1 + avg_g / avg_l), 1)
  ```
- **修复建议**: 请根据上下文手动审查


### 89. [MEDIUM] undefined
- **文件**: `gbt\tech_analysis.py:16`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return round(sum(values[-period:]) / period, 2)
  ```
- **修复建议**: 请根据上下文手动审查


### 90. [MEDIUM] undefined
- **文件**: `gbt\tech_analysis.py:23`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  k = 2 / (period + 1)
  ```
- **修复建议**: 请根据上下文手动审查


### 91. [MEDIUM] undefined
- **文件**: `gbt\tool.py:58`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return False
  ```
- **修复建议**: 请根据上下文手动审查


### 92. [MEDIUM] undefined
- **文件**: `gbt\tool.py:90`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  lines = []
  ```
- **修复建议**: 请根据上下文手动审查


### 93. [MEDIUM] undefined
- **文件**: `gbt\trader.py:434`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return TradeSignal(code, quote.name, "hold", quote.price, reason=f"异常:{e}", conf
  ```
- **修复建议**: 请根据上下文手动审查


### 94. [MEDIUM] undefined
- **文件**: `gbt\trader.py:663`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  self.running = True
  ```
- **修复建议**: 请根据上下文手动审查


### 95. [MEDIUM] undefined
- **文件**: `gbt\trader.py:795`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return {"ok": False, "error": f"未知: {platform_name}"}
  ```
- **修复建议**: 请根据上下文手动审查


### 96. [MEDIUM] undefined
- **文件**: `gbt\watcher.py:175`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  r = subprocess.run(["ping", "-n", "1", "-w", "2000", "8.8.8.8"],
  ```
- **修复建议**: 请根据上下文手动审查


### 97. [MEDIUM] undefined
- **文件**: `gbt\watcher.py:475`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  r = subprocess.run(["ping", "-n", "2", "8.8.8.8"], capture_output=True, text=True, timeout=6, errors='replace')
  ```
- **修复建议**: 请根据上下文手动审查


### 98. [MEDIUM] undefined
- **文件**: `gbt\watcher_agent.py:594`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return self.agent.detect_hallucination(response_text, source)
  ```
- **修复建议**: 请根据上下文手动审查


### 99. [MEDIUM] undefined
- **文件**: `gbt\winctl.py:79`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return WinResult(True,"keyboard","hotkey",data=keys)
  ```
- **修复建议**: 请根据上下文手动审查


### 100. [MEDIUM] undefined
- **文件**: `gbt\winctl.py:93`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return WinResult(True,"mouse","click",data=button)
  ```
- **修复建议**: 请根据上下文手动审查


### 101. [MEDIUM] undefined
- **文件**: `gbt\winctl.py:272`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return WinResult(True,"clip","set",data=f"复制{len(text)}字")
  ```
- **修复建议**: 请根据上下文手动审查


### 102. [MEDIUM] undefined
- **文件**: `start_demo.py:25`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return "<h1>GBT v2.0</h1>"
  ```
- **修复建议**: 请根据上下文手动审查


### 103. [MEDIUM] undefined
- **文件**: `tools\mcp_tools.py:15`
- **CVSS 预估**: 4.0-6.9 (估算参考)
- **赏金预估**: 参考: $100-$500
- **代码片段**: 
  ```
  return f"❌ {server}: {result.error}"
  ```
- **修复建议**: 请根据上下文手动审查


---
> ⚠️ 此报告仅供授权安全测试使用。请遵循负责任披露原则。
> 生成: GBT小土豆全能开发者 — 白帽模式
