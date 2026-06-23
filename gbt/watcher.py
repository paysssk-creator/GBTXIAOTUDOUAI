"""
守夜人 (Night Watcher) — 安全监控与自动修复引擎
启动即运行，实时监控所有连接点，发现异常自动上报AI并执行修复。
"""
import os, sys, time, threading, json, logging, subprocess, re
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Watcher")
from gbt import DEFAULT_PING_TARGET

# 模块级单例引用 — 供外部通过 from gbt.watcher import watcher 获取
watcher = None

class Alert:
    """告警记录"""
    def __init__(self, source, level, message, detail=""):
        self.id = f"{int(time.time()*1000)}-{source}"
        self.source = source      # network / process / filesystem / registry / wifi / log
        self.level = level        # info / warn / critical
        self.message = message
        self.detail = detail
        self.time = datetime.now().strftime("%H:%M:%S")
        self.fixed = False
        self.fix_result = ""

class NightWatcher:
    """守夜人引擎 — 统一管理所有安全监控点"""
    
    def __init__(self, llm=None, project_root=None):
        self.llm = llm
        self.project_root = project_root or os.path.dirname(os.path.dirname(__file__))
        self.running = False
        self.threads = {}
        self.alerts = deque(maxlen=200)
        self.monitor_status = {}  # source -> {"status":"ok|warn|error", "last_check":"", "details":""}
        self._lock = threading.Lock()
        self.fix_log = deque(maxlen=100)
        self.auto_fix_enabled = True
        # 注册为模块级单例
        import gbt.watcher as _mod
        _mod.watcher = self
        
        # 初始化所有监控状态
        for src in ["network", "process", "filesystem", "registry", "wifi", "logs", "disk", "connections"]:
            self.monitor_status[src] = {"status": "idle", "last_check": "", "details": "", "alerts": 0}
    
    def _add_alert(self, source, level, message, detail=""):
        a = Alert(source, level, message, detail)
        with self._lock:
            self.alerts.appendleft(a)
            self.monitor_status[source]["alerts"] += 1
            if level in ("warn", "critical"):
                self.monitor_status[source]["status"] = "warn" if level == "warn" else "error"
        L.warning(f"[{source.upper()}] {level}: {message}")
        
        # 自动修复
        if self.auto_fix_enabled and level in ("warn", "critical") and self.llm:
            threading.Thread(target=self._auto_fix, args=(a,), daemon=True).start()
        
        # 🧠 唤醒自主大脑 — 告警触发立即通知
        if level in ("warn", "critical"):
            try:
                from gbt.brain import brain as _br
                if _br.running:
                    _br.ping("watcher", f"{source}: {message[:60]}")
            except Exception as e:
                L.debug(f"Brain ping 失败: {e}")
        
        return a
    
    def _auto_fix(self, alert):
        """AI自动修复"""
        try:
            prompt = f"""安全告警 [{alert.source}] {alert.level}: {alert.message}
详情: {alert.detail}
请分析问题原因并给出具体的修复步骤。回复格式:
修复建议: (简短说明)
命令: (如果需要执行的命令, 否则写 NONE)"""
            
            msgs = [{"role": "system", "content": "你是GBT安全工程师,负责诊断和修复系统安全问题。回复简洁专业。"},
                    {"role": "user", "content": prompt}]
            resp = self.llm.invoke(msgs)
            
            alert.fix_result = resp[:500]
            alert.fixed = "修复建议" in resp
            
            # 尝试执行修复命令 — 安全白名单制
            cmd_match = re.search(r'命令:\s*(.+)', resp)
            if cmd_match:
                cmd = cmd_match.group(1).strip()
                if cmd.upper() != "NONE":
                    # 白名单：系统诊断命令 + MCP恢复操作
                    safe_cmds = ["ping", "ipconfig", "netstat", "tasklist", "sc", "netsh",
                                "chkdsk", "sfc", "dism", "cleanmgr", "reg", "wmic",
                                "systeminfo", "whoami", "net", "dir", "del", "mkdir",
                                # MCP恢复命令
                                "node", "npm", "npx", "python", "python3",
                                "git", "cls", "echo", "type", "where"]
                    first_word = cmd.split()[0].lower() if cmd.split() else ""
                    if first_word not in safe_cmds:
                        alert.fix_result += f"\n⚠️ 命令被拦截(安全策略): {cmd}"
                    else:
                        try:
                            r = subprocess.run(cmd, shell=False, capture_output=True,
                                text=True, timeout=30, errors='replace')
                            alert.fix_result += f"\n✅ 命令已执行: {cmd}\n输出: {r.stdout[:200]}"
                            alert.fixed = True
                        except Exception as e:
                            alert.fix_result += f"\n❌ 命令执行失败: {e}"
            
            with self._lock:
                self.fix_log.appendleft({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "alert": alert.message[:80],
                    "result": "已修复" if alert.fixed else "需人工",
                    "detail": alert.fix_result[:200]
                })
        except Exception as e:
            alert.fix_result = f"AI修复异常: {e}"
            L.error(f"自动修复失败: {e}")
    
    def start(self):
        """启动所有监控线程"""
        if self.running:
            return {"ok": False, "msg": "守夜人已在运行"}
        
        self.running = True
        
        # 网络监控 - 每30秒
        self.threads["network"] = threading.Thread(target=self._watch_network, daemon=True)
        self.threads["network"].start()
        
        # 进程监控 - 每60秒
        self.threads["process"] = threading.Thread(target=self._watch_process, daemon=True)
        self.threads["process"].start()
        
        # 文件系统监控 - 每45秒
        self.threads["filesystem"] = threading.Thread(target=self._watch_filesystem, daemon=True)
        self.threads["filesystem"].start()
        
        # 注册表监控 - 每120秒
        self.threads["registry"] = threading.Thread(target=self._watch_registry, daemon=True)
        self.threads["registry"].start()
        
        # WiFi监控 - 每90秒
        self.threads["wifi"] = threading.Thread(target=self._watch_wifi, daemon=True)
        self.threads["wifi"].start()
        
        # 磁盘监控 - 每60秒
        self.threads["disk"] = threading.Thread(target=self._watch_disk, daemon=True)
        self.threads["disk"].start()
        
        # 日志监控 - 每20秒
        self.threads["logs"] = threading.Thread(target=self._watch_logs, daemon=True)
        self.threads["logs"].start()
        # MCP连接监控
        self.threads["connections"] = threading.Thread(target=self._watch_connections, daemon=True)
        self.threads["connections"].start()
        
        L.info(f"🛡️ 守夜人已启动 — {len(self.threads)}个监控点就绪")
        return {"ok": True, "monitors": len(self.threads)}
    
    def stop(self):
        self.running = False
        for src in self.monitor_status:
            self.monitor_status[src]["status"] = "idle"
        L.info("守夜人已停止")
    
    # ── 网络监控 ──
    def _watch_network(self):
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                # Ping 外网
                _PH = os.getenv("PING_TARGET", DEFAULT_PING_TARGET)
                r = subprocess.run(["ping", "-n", "1", "-w", "2000", _PH],
                    capture_output=True, text=True, timeout=5, errors='replace')
                if r.returncode != 0:
                    self._add_alert("network", "critical", "网络中断 — 无法连接 8.8.8.8",
                                    f"ping 返回码: {r.returncode}")
                else:
                    # 提取延迟
                    m = re.search(r'时间[=<](\d+)ms', r.stdout)
                    latency = int(m.group(1)) if m else 0
                    if latency > 500:
                        self._add_alert("network", "warn", f"网络延迟过高: {latency}ms",
                                        "可能存在网络拥塞")
                    self.monitor_status["network"] = {"status": "ok", "last_check": now,
                        "details": f"延迟 {latency}ms" if latency else "正常"}
                
                # DNS 测试
                rd = subprocess.run(["nslookup", "google.com"], capture_output=True, text=True, timeout=5, errors='replace')
                if rd.returncode != 0:
                    self._add_alert("network", "warn", "DNS解析异常", rd.stderr[:200])
                
            except Exception as e:
                self._add_alert("network", "critical", f"网络监控异常: {e}")
                self.monitor_status["network"]["status"] = "error"
            
            time.sleep(30)
    
    # ── 进程监控 ──
    def _watch_process(self):
        suspicious = ["mimikatz", "nmap", "wireshark", "netcat", "nc.exe", "psexec",
                      "keylogger", "hook", "inject", "meterpreter", "beacon"]
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=10, errors='replace')
                found = []
                for line in r.stdout.lower().split("\n"):
                    for s in suspicious:
                        if s in line and "gbt" not in line.lower():
                            found.append(s)
                
                if found:
                    self._add_alert("process", "warn",
                        f"检测到可疑进程特征: {', '.join(set(found))}",
                        "请确认是否为合法进程")
                    self.monitor_status["process"] = {"status": "warn", "last_check": now,
                        "details": f"可疑: {len(set(found))}"}
                else:
                    self.monitor_status["process"] = {"status": "ok", "last_check": now,
                        "details": "无异常"}
            except Exception as e:
                self._add_alert("process", "critical", f"进程监控异常: {e}")
                self.monitor_status["process"]["status"] = "error"
            
            time.sleep(60)
    
    # ── 文件系统监控 ──
    def _watch_filesystem(self):
        watch_dirs = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
            os.path.expanduser("~\\Desktop"),
            "C:\\Windows\\Temp",
        ]
        prev_snapshot = {}
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                changes = []
                for d in watch_dirs:
                    if not os.path.isdir(d):
                        continue
                    current = set()
                    for f in os.listdir(d):
                        fp = os.path.join(d, f)
                        try:
                            current.add((f, os.path.getsize(fp) if os.path.isfile(fp) else 0))
                        except Exception as e:
                            L.debug(f"文件信息读取失败 {fp}: {e}")
                    
                    if d in prev_snapshot:
                        new_files = current - prev_snapshot[d]
                        if new_files:
                            for nf, sz in new_files:
                                if nf.endswith(('.exe', '.bat', '.ps1', '.vbs', '.scr')):
                                    changes.append(f"⚠️ 新增可执行: {nf}")
                                else:
                                    changes.append(f"📄 新增: {nf}")
                    
                    prev_snapshot[d] = current
                
                if changes:
                    self._add_alert("filesystem", "warn",
                        f"文件系统变更: {len(changes)}个文件",
                        "\n".join(changes[:5]))
                    self.monitor_status["filesystem"] = {"status": "warn", "last_check": now,
                        "details": f"{len(changes)} 变更"}
                else:
                    self.monitor_status["filesystem"] = {"status": "ok", "last_check": now,
                        "details": "无变更"}
            except Exception as e:
                self.monitor_status["filesystem"]["status"] = "error"
                self.monitor_status["filesystem"]["details"] = str(e)[:100]
            
            time.sleep(45)
    
    # ── 注册表监控 ──
    def _watch_registry(self):
        keys = [
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        ]
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                for key in keys:
                    r = subprocess.run(["reg", "query", key], capture_output=True, text=True, timeout=10, shell=False, errors='replace')
                    entries = [l.strip() for l in r.stdout.split("\n") if l.strip() and "REG_" in l]
                    suspicious = [e for e in entries if any(s in e.lower() for s in
                        ["temp", "appdata", "unknown", "crack", "hack"])]
                    if suspicious:
                        self._add_alert("registry", "warn",
                            f"可疑注册表启动项: {len(suspicious)}个",
                            "\n".join(suspicious[:3]))
                
                self.monitor_status["registry"] = {"status": "ok", "last_check": now,
                    "details": f"已扫描 {len(keys)} 项"}
            except Exception as e:
                self.monitor_status["registry"]["status"] = "warn"
                self.monitor_status["registry"]["details"] = str(e)[:100]
            
            time.sleep(120)
    
    # ── WiFi监控 ──
    def _watch_wifi(self):
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                r = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True, timeout=10, errors='replace')
                
                if "没有" in r.stdout or "not running" in r.stdout.lower():
                    self.monitor_status["wifi"] = {"status": "ok", "last_check": now,
                        "details": "WiFi未连接"}
                else:
                    # 提取信号强度
                    sig = re.search(r'信号\s*:\s*(\d+)%', r.stdout)
                    signal = int(sig.group(1)) if sig else 100
                    ssid = re.search(r'SSID\s*:\s*(.+)', r.stdout)
                    ssid_name = ssid.group(1).strip() if ssid else "未知"
                    
                    if signal < 30:
                        self._add_alert("wifi", "warn", f"WiFi信号弱: {signal}% ({ssid_name})")
                    
                    self.monitor_status["wifi"] = {"status": "ok", "last_check": now,
                        "details": f"{ssid_name} {signal}%"}
            except Exception as e:
                self.monitor_status["wifi"]["status"] = "ok"
                self.monitor_status["wifi"]["details"] = "无WiFi适配器"
            
            time.sleep(90)
    
    # ── 磁盘监控 ──
    def _watch_disk(self):
        while self.running:
            try:
                import ctypes
                now = datetime.now().strftime("%H:%M:%S")
                free = ctypes.c_uint64(); total = ctypes.c_uint64(); tfree = ctypes.c_uint64()
                ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\", ctypes.byref(free),
                    ctypes.byref(total), ctypes.byref(tfree))
                
                free_gb = round(free.value / (1024**3), 1)
                total_gb = round(total.value / (1024**3), 1)
                if total_gb <= 0:
                    self.monitor_status["disk"] = {"status": "error", "last_check": now, "details": "无法获取磁盘信息"}
                    time.sleep(300)
                    continue
                pct = round((total_gb - free_gb) / total_gb * 100, 1)
                
                if free_gb < 5:
                    self._add_alert("disk", "critical",
                        f"磁盘空间不足: 仅剩 {free_gb}GB ({pct}%)",
                        "建议清理临时文件和不必要的程序")
                elif free_gb < 10:
                    self._add_alert("disk", "warn",
                        f"磁盘空间偏低: {free_gb}GB ({pct}%)")
                
                self.monitor_status["disk"] = {"status": "ok", "last_check": now,
                    "details": f"剩余 {free_gb}GB / {total_gb}GB"}
            except Exception as e:
                self.monitor_status["disk"]["status"] = "error"
                self.monitor_status["disk"]["details"] = str(e)[:100]
            
            time.sleep(60)
    
    # ── 日志监控 ──
    def _watch_logs(self):
        """实时监控GBT日志和Windows事件日志"""
        log_path = os.path.join(self.project_root, "desktop", "app.log")
        cursor = 0
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                # 监控 GBT 自身日志
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(cursor)
                        new_lines = f.read()
                        cursor = f.tell()
                        if new_lines:
                            for line in new_lines.strip().split("\n"):
                                if any(kw in line.lower() for kw in
                                    ["error", "fail", "exception", "traceback", "denied", "forbidden"]):
                                    self._add_alert("logs", "warn",
                                        f"日志异常: {line[:120]}", "")
                
                self.monitor_status["logs"] = {"status": "ok", "last_check": now,
                    "details": "监控中"}
            except Exception as e:
                L.debug(f"日志监控异常: {e}")
                self.monitor_status["logs"]["status"] = "ok"
                self.monitor_status["logs"]["details"] = "等待日志"
            
            time.sleep(20)
    
    # ── MCP连接监控 ──
    def _watch_connections(self):
        """实时监控所有MCP服务器连接状态，自动检测断连和恢复"""
        time.sleep(10)  # 等MCP初始化
        while self.running:
            try:
                now = datetime.now().strftime("%H:%M:%S")
                self.monitor_status["connections"] = {
                    "status": "checking", "last_check": now,
                    "details": "正在检测MCP服务器..."
                }
                
                from gbt.mcp import get_mcp, call_mcp
                mcp = get_mcp()
                total = len(mcp._s)
                online = 0
                down = []
                
                for name, srv in mcp._s.items():
                    try:
                        r = call_mcp(name, "status", timeout=2)
                        if r.ok:
                            online += 1
                        else:
                            down.append(f"{name}(rc={r.error or '?'})")
                    except Exception as e:
                        down.append(f"{name}({str(e)[:30]})")
                    # 增量更新
                    self.monitor_status["connections"] = {
                        "status": "checking",
                        "last_check": now,
                        "details": f"检测中... {online+len(down)}/{total}"
                    }
                
                status = "ok" if not down else ("warn" if len(down) <= 2 else "critical")
                self.monitor_status["connections"] = {
                    "status": status,
                    "last_check": now,
                    "details": f"{online}/{total} 在线" + (f", 断连: {'; '.join(down[:5])}" if down else "")
                }
                
                # 断连告警
                if down:
                    L.warning(f"🔌 连接断连: {len(down)}/{total} — {'; '.join(down[:3])}")
                    self._add_alert("connections",
                        "critical" if len(down) > 3 else "warn",
                        f"{len(down)}个MCP服务断连",
                        "; ".join(down[:5]))
                
            except Exception as e:
                self.monitor_status["connections"] = {"status": "error", "last_check": now, "details": str(e)[:100]}
            
            time.sleep(30)
    
    def get_status(self):
        """获取完整监控状态"""
        with self._lock:
            return {
                "running": self.running,
                "monitors": dict(self.monitor_status),
                "recent_alerts": [
                    {"id": a.id, "source": a.source, "level": a.level,
                     "message": a.message, "time": a.time, "fixed": a.fixed}
                    for a in list(self.alerts)[:20]
                ],
                "fix_log": list(self.fix_log)[:20],
                "auto_fix": self.auto_fix_enabled
            }
    
    def run_scan(self, target):
        """手动触发单次扫描"""
        results = {}
        now = datetime.now().strftime("%H:%M:%S")
        
        if target == "network" or target == "all":
            try:
                _PH = os.getenv("PING_TARGET", DEFAULT_PING_TARGET)
                r = subprocess.run(["ping", "-n", "2", _PH], capture_output=True, text=True, timeout=6, errors='replace')
                results["network"] = {"ok": r.returncode == 0, "output": r.stdout[-200:]}
            except Exception as e:
                L.warning(f"网络扫描失败: {e}")
                results["network"] = {"ok": False, "output": f"扫描超时: {e}"}
        
        if target == "process" or target == "all":
            try:
                r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=10, errors='replace')
                count = len([l for l in r.stdout.split("\n") if l.strip()])
                results["process"] = {"ok": True, "output": f"活跃进程: {count}"}
            except Exception as e:
                L.warning(f"进程扫描失败: {e}")
                results["process"] = {"ok": False, "output": f"扫描失败: {e}"}
        
        if target == "disk" or target == "all":
            try:
                import ctypes
                free = ctypes.c_uint64(); total = ctypes.c_uint64(); tfree = ctypes.c_uint64()
                ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\", ctypes.byref(free), ctypes.byref(total), ctypes.byref(tfree))
                results["disk"] = {"ok": True,
                    "output": f"剩余 {round(free.value/(1024**3),1)}GB / {round(total.value/(1024**3),1)}GB"}
            except Exception as e:
                L.warning(f"磁盘扫描失败: {e}")
                results["disk"] = {"ok": False, "output": f"扫描失败: {e}"}
        
        return results