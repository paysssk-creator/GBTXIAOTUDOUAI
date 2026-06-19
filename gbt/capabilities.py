"""
capabilities.py — GBT 能力注册表
统一注册所有能力到智能路由器
v3.0: +屏幕OCR +语音 +精准抓取 +操盘流水线
"""
import os, sys, re, logging
from gbt.router import Capability, router

L = logging.getLogger("GBT.Capabilities")


def _handler_browser_open(text):
    """打开浏览器"""
    url = "https://www.bing.com"
    import re
    m = re.search(r'(https?://[^\s\u4e00-\u9fff]+)', text)
    if m:
        url = m.group(1)
    os.startfile(url)
    return f"已打开浏览器 → {url}"


def _handler_maximize(text):
    """最大化窗口"""
    from gbt.desktop_ctl import desktop_ctl
    desktop_ctl.maximize_window()
    return "窗口已最大化"


def _handler_screenshot(text):
    """截图"""
    import pyautogui, time
    ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
    os.makedirs(ss_dir, exist_ok=True)
    fp = os.path.join(ss_dir, f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
    pyautogui.screenshot(fp)
    return f"截图已保存 → {fp}"


def _handler_stock_lookup(text):
    """查询股票"""
    import re
    # 匹配6位数字股票代码 (不依赖\b, 兼容中文环境)
    m = re.search(r'(?<!\d)(\d{6})(?!\d)', text)
    if not m:
        return "未找到股票代码（需要6位数字代码）"
    code = m.group(1)
    trader = router.get_dep("trader")
    if not trader:
        return "交易引擎未就绪"
    try:
        q = trader.fetch_quote([code])
        if code in q:
            qt = q[code]
            name = getattr(qt, 'name', code)
            price = getattr(qt, 'price', 0)
            pct = getattr(qt, 'change_pct', 0)
            return f"{name}({code}): ¥{price} | {pct:+.2f}%"
    except Exception as e:
        return f"查询失败: {e}"
    return f"未找到 {code} 的行情数据"


def _handler_system_status(text):
    """系统状态"""
    trader = router.get_dep("trader")
    watcher = router.get_dep("watcher")
    brain = router.get_dep("brain")
    lines = []
    if brain:
        bs = brain.get_status()
        lines.append(f"大脑: {'运行中' if bs.get('running') else '已停止'} | {bs['heartbeat']['count']} 心跳")
    if trader:
        ts = trader.get_status()
        lines.append(f"交易: auto_trade={'ON' if ts.get('auto_trade') else 'OFF'} | {ts.get('watchlist_count',0)} 自选")
    if watcher:
        ws = watcher.get_status()
        ok = sum(1 for m in ws.get('monitors',{}).values() if m.get('status')=='ok')
        total = len(ws.get('monitors',{}))
        lines.append(f"监控: {ok}/{total} 正常")
    return "\n".join(lines) if lines else "系统未完全就绪"


def _handler_watchlist(text):
    """自选股列表"""
    trader = router.get_dep("trader")
    if not trader:
        return "交易引擎未就绪"
    wl = getattr(trader, 'watchlist', {}) or {}
    if not wl:
        return "自选股列表为空"
    lines = ["📋 自选股:"]
    for i, (code, name) in enumerate(list(wl.items())[:10]):
        lines.append(f"  {code} {name}")
    if len(wl) > 10:
        lines.append(f"  ... 共 {len(wl)} 只")
    return "\n".join(lines)


def _handler_account(text):
    """账户查询"""
    account = router.get_dep("account")
    if not account:
        return "账户系统未就绪"
    try:
        pos_count = len(account.positions) if hasattr(account, 'positions') else 0
        return (f"💰 模拟账户: ¥{account.cash:,.0f}\n"
                f"📊 持仓: {pos_count} 只\n"
                f"📈 总盈亏: ¥{account.total_pnl:+,.0f}")
    except:
        return f"账户查询异常"


def _handler_scan_market(text):
    """市场扫描"""
    trader = router.get_dep("trader")
    if not trader:
        return "交易引擎未就绪"
    try:
        data = trader.fetch_watchlist()
        up = sum(1 for q in data.values() if getattr(q, 'change_pct', 0) > 0)
        down = sum(1 for q in data.values() if getattr(q, 'change_pct', 0) < 0)
        return f"📊 自选股: {len(data)}只 | 🟢上涨{up} | 🔴下跌{down}"
    except Exception as e:
        return f"扫描失败: {e}"


def _handler_watcher_check(text):
    """守夜人检查"""
    watcher = router.get_dep("watcher")
    if not watcher:
        return "守夜人未就绪"
    ws = watcher.get_status()
    lines = ["🛡️ 守夜人监控:"]
    for name, st in ws.get('monitors', {}).items():
        icon = "✅" if st.get('status') == 'ok' else "⚠️"
        detail = st.get('details', '')[:40]
        lines.append(f"  {icon} {name}: {detail}")
    return "\n".join(lines)


def _handler_notify(text):
    """发送通知"""
    import subprocess
    msg = text.replace("通知", "").replace("提醒", "").strip()[:100] or "GBT通知"
    ps = f'''
    Add-Type -AssemblyName System.Windows.Forms
    $n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Information
    $n.Visible = $true
    $n.ShowBalloonTip(5000, "GBT 通知", "{msg}", "Info")
    '''
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                  capture_output=True, timeout=5, text=True, errors='replace')
    return f"已发送通知: {msg}"


def _handler_trade(text):
    """自主交易 — 实际执行全链路分析管道"""
    import re
    m = re.search(r'(?<!\d)(\d{6})(?!\d)', text)
    if not m:
        return "请提供6位股票代码"
    code = m.group(1)
    
    trader = router.get_dep("trader")
    account = router.get_dep("account")
    brain = router.get_dep("brain")
    
    results = []
    price = 0  # 默认值
    
    # Step 1: 获取实时行情
    try:
        q = trader.fetch_quote([code])
        if code in q:
            qt = q[code]
            name = getattr(qt, 'name', code)
            price = getattr(qt, 'price', 0) or 0
            pct = getattr(qt, 'change_pct', 0)
            results.append(f"📊 {name}({code}): ¥{price} ({pct:+.2f}%)")
        else:
            results.append(f"⚠️ {code}: 未获取到行情(可能停牌或非交易时段)")
    except Exception as e:
        results.append(f"❌ 行情获取失败: {e}")
        return "\n".join(results)
    
    # Step 2: 技术分析
    try:
        from gbt.tech_analysis import RSI, MACD, BollingerBands
        kline = trader.fetch_kline(code, 240, 30)
        if kline:
            # 处理两种K线格式: 数组格式 {"closes":[...]} 或 列表格式 [{close:...}, ...]
            if isinstance(kline, dict) and kline.get("ok"):
                closes = kline.get("closes", [])
            elif isinstance(kline, list):
                closes = [float(k.get('close', 0)) if isinstance(k, dict) else 0 for k in kline]
                closes = [c for c in closes if c > 0]
            else:
                closes = []
            
            if len(closes) >= 10:
                rsi_result = RSI(closes)
                rsi_v = rsi_result.get('rsi', 50) if isinstance(rsi_result, dict) else float(rsi_result)
                rsi_zone = rsi_result.get('zone', '') if isinstance(rsi_result, dict) else ''
                macd_d = MACD(closes)
                boll_d = BollingerBands(closes)
                last_close = closes[-1]
                bb_upper = boll_d.get('upper', 0) or 0
                bb_lower = boll_d.get('lower', 0) or 0
                bb_pos = '上轨' if last_close >= bb_upper else ('下轨' if last_close <= bb_lower else '中轨')
                macd_trend = macd_d.get('trend', '')
                mc = '金叉' if '金叉' in str(macd_trend) else ('死叉' if '死叉' in str(macd_trend) else '震荡')
                results.append(f"📈 RSI={rsi_v:.1f} | MACD={mc} | 布林={bb_pos}")
            else:
                results.append(f"📈 K线数据不足({len(closes)}根)，需要至少10根")
    except Exception as e:
        results.append(f"📈 技术分析暂不可用: {e}")
    
    # Step 3: AI 策略评分
    try:
        if code in q:
            signal = trader.analyze_with_ai(code, q[code])
            if signal:
                action = getattr(signal, 'action', 'hold')
                conf = getattr(signal, 'confidence', 0)
                reason = getattr(signal, 'reason', '')[:150] or '策略综合评分'
                results.append(f"🧠 AI分析: {action.upper()} | 置信度: {conf}%")
                results.append(f"💡 理由: {reason}")
    except Exception as e:
        results.append(f"🧠 AI分析暂不可用: {e}")
    
    # Step 4: 风控审批
    try:
        from gbt.risk_ctrl import risk_mgr
        # 构造风控所需的信号对象
        class _SimpleSignal:
            def __init__(self):
                self.action = "buy" if any(kw in text for kw in ["买入","buy"]) else "sell"
                self.code = code
                self.price = price
                self.confidence = 70
                self.reason = "用户触发"
        sig = _SimpleSignal()
        approval = risk_mgr.approve_trade(sig, trader.positions)
        if isinstance(approval, dict):
            if approval.get("approved"):
                results.append(f"🛡️ 风控: ✅ 通过 | 建议操作: {approval.get('action','?').upper()} | 置信度: {approval.get('confidence',0)}%")
            else:
                results.append(f"🛡️ 风控: ❌ 拒绝 | 原因: {', '.join(approval.get('issues',['未知']))}")
        else:
            results.append(f"🛡️ 风控: {approval}")
    except Exception as e:
        results.append(f"🛡️ 风控暂不可用: {e}")
    
    # Step 5: 唤醒大脑记录决策
    if brain:
        brain.ping("user_trade", f"交易分析: {code}")
    
    return "\n".join(results)


# ═══════════════════════════════════════════════════════
# 编程/黑客能力
# ═══════════════════════════════════════════════════════

def _handler_web_search(text):
    """网络搜索"""
    import urllib.parse
    query = text
    for kw in ["搜索", "查一下", "search", "百度"]:
        query = query.replace(kw, "")
    query = query.strip()[:200] or "A股最新消息"
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    os.startfile(url)
    return f"已搜索: {query} → 浏览器已打开"


def _handler_file_op(text):
    """文件操作"""
    import re
    # 读文件
    m = re.search(r'(?:读|打开|查看)\s*(?:文件)?\s*["\']?([^"\'\s]+(?:\.[a-zA-Z]+))', text)
    if m:
        fpath = m.group(1)
        if not os.path.isabs(fpath):
            fpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), fpath)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()[:2000]
                return f"📄 {os.path.basename(fpath)} ({len(content)}字符):\n{content[:500]}"
            except:
                return f"无法读取: {fpath}"
        return f"文件不存在: {fpath}"
    return "请指定要读取的文件路径"


def _handler_code_exec(text):
    """执行代码"""
    import subprocess, re
    # Extract code block or command
    code_m = re.search(r'```(?:python)?\s*\n?(.*?)```', text, re.DOTALL)
    if code_m:
        code = code_m.group(1).strip()
        try:
            r = subprocess.run(["python", "-c", code],
                              capture_output=True, text=True, timeout=10,
                              errors='replace')
            out = (r.stdout + r.stderr)[:1000] or "(执行完成，无输出)"
            return f"⚡ 代码执行结果:\n{out}"
        except subprocess.TimeoutExpired:
            return "⏱ 代码执行超时(>10s)"
        except Exception as e:
            return f"❌ 执行失败: {e}"
    # Shell command
    cmd_m = re.search(r'(?:执行|运行|cmd|shell)\s*[:：]?\s*(.+)', text, re.IGNORECASE)
    if cmd_m:
        cmd = cmd_m.group(1).strip()[:200]
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=10, errors='replace')
            out = (r.stdout + r.stderr)[:1000] or "(执行完成)"
            return f"⚡ Shell执行:\n{out}"
        except Exception as e:
            return f"❌ Shell失败: {e}"
    return "请提供要执行的代码或命令 (用 ```python ... ``` 或 执行: ...)"


# ═══════════════════════════════════════════════════
# New v3.0: 屏幕AI + 语音 + 精准抓取 + 操盘流水线
# ═══════════════════════════════════════════════════

def _handler_screen_ocr(text):
    """屏幕OCR — 识别桌面文字"""
    try:
        from gbt.screen_ai import ScreenOCR
        import re
        # 可选区域: OCR 左上角 100,50 右下角 500,300
        region = None
        m = re.search(r'(\d+)\s*[,，]\s*(\d+)\s*[,，]\s*(\d+)\s*[,，]\s*(\d+)', text)
        if m:
            l, t, w, h = map(int, m.groups())
            region = (l, t, w, h)
        ocr = ScreenOCR()
        r = ocr.read_text(region=region)
        if r["ok"]:
            lines = r.get("lines", [])
            preview = "\n".join(lines[:15])
            if not preview.strip():
                preview = r["text"][:500]
            return f"👁 屏幕OCR识别 ({r['word_count']}词):\n{preview}"
        return f"OCR失败: {r.get('error', '未知错误')}"
    except Exception as e:
        return f"OCR异常: {e}"


def _handler_voice_speak(text):
    """语音朗读"""
    try:
        from gbt.screen_ai import Voice
        import re
        # 提取要朗读的文字
        speak_text = text
        m = re.search(r'(?:说|朗读|语音|讲话|speak)\s*[:：]?\s*(.+)', text, re.IGNORECASE)
        if m:
            speak_text = m.group(1).strip()[:200]
        elif any(kw in text for kw in ["说", "朗读", "语音"]):
            speak_text = text.split("说")[-1].split("朗读")[-1].strip()[:200]
        r = Voice.speak(speak_text)
        return f"🗣 已朗读: {speak_text[:60]}" if r["ok"] else f"语音失败: {r.get('error','')}"
    except Exception as e:
        return f"语音异常: {e}"


def _handler_login_detect(text):
    """检测券商登录状态"""
    try:
        from gbt.screen_ai import ScreenOCR, Voice
        ocr = ScreenOCR()
        r = ocr.detect_login_state()
        if r["logged_in"]:
            Voice.speak("登录已确认，GBT 接手自主操盘")
            return f"✅ 已登录 (置信度 {r['confidence']}) | 关键词: {r['found_keywords']}"
        return f"⚠ 未检测到登录 (置信度 {r['confidence']}) | 找到: {r.get('found_keywords', [])} | 屏幕: {r.get('screen_text', '')[:100]}"
    except Exception as e:
        return f"登录检测异常: {e}"


def _handler_precision_scrape(text):
    """精准资讯抓取 — 多源交叉验证"""
    import urllib.request, json
    results = {}
    try:
        # 提取搜索目标
        target = text
        m = re.search(r'(?:抓取|资讯|新闻|scrape)\s*[:：]?\s*(.+)', text, re.IGNORECASE)
        if m:
            target = m.group(1).strip()
        
        # Source 1: 新浪财经快讯
        try:
            url = "https://hq.sinajs.cn/list=sh000001"
            req = urllib.request.Request(url, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0"
            })
            raw = urllib.request.urlopen(req, timeout=8).read().decode("gbk", errors="replace")
            parts = raw.split(",")
            if len(parts) > 3:
                results["上证指数"] = f"{parts[0]}: {parts[1]} ({parts[3]}%)"
        except:
            results["上证指数"] = "获取失败"
        
        # Source 2: Web search (use DDG/bing fallback)
        try:
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            search_url = f"https://api.duckduckgo.com/?q={urllib.request.quote(target)}&format=json&no_html=1"
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=10)
            ddg = json.loads(resp.read().decode())
            abstract = ddg.get("AbstractText", "") or ddg.get("Abstract", "")
            if abstract:
                results["DDG摘要"] = abstract[:300]
            topics = ddg.get("RelatedTopics", [])
            if topics:
                results["相关条目"] = len(topics)
                results["首条"] = topics[0].get("Text", "")[:200] if topics else ""
        except Exception as e:
            results["DDG"] = f"搜索受限: {str(e)[:60]}"
        
        summary = "\n".join(f"  [{k}] {v}" for k, v in results.items())
        return f"🎯 精准抓取 [{target}]:\n{summary}"
    except Exception as e:
        return f"抓取异常: {e}"


def _handler_auto_pipeline(text):
    """自主操盘流水线"""
    try:
        from gbt.screen_ai import AutoPipeline
        import re
        # 提取平台URL
        url = "https://trade.eastmoney.com"  # 默认东方财富
        m = re.search(r'(https?://[^\s]+)', text)
        if m:
            url = m.group(1)
        # 提取平台名
        platform = "券商平台"
        m2 = re.search(r'(?:平台|用)\s*[:：]?\s*(.{2,10})', text)
        if m2:
            platform = m2.group(1).strip()
        
        pipeline = AutoPipeline()
        r = pipeline.run_login_flow(url, platform)
        if r["ok"]:
            return f"🚀 操盘流水线启动: {r['phase']} | {r['message']}"
        return f"⚠ 流水线: {r['phase']} — {r.get('message', r.get('error', ''))}"
    except Exception as e:
        return f"流水线异常: {e}"


def register_all():
    """注册所有能力到路由器"""
    caps = [
        # ═══ 桌面操控 ═══
        Capability("browser_open", "desktop", "打开浏览器/网页",
                   ["打开浏览器", "打开edge", "打开chrome", "打开网页", "上网", "浏览"],
                   _handler_browser_open, priority=9),

        Capability("window_maximize", "desktop", "最大化/全屏窗口",
                   ["最大化", "全屏", "最大化窗口", "放大", "窗口放大", "窗口最大化"],
                   _handler_maximize, priority=7),

        Capability("screenshot", "desktop", "屏幕截图",
                   ["截图", "截屏", "屏幕截图", "拍屏", "截个图", "拍个"],
                   _handler_screenshot, priority=6),

        # ═══ 交易/行情 ═══
        Capability("stock_lookup", "trading", "查询股票实时行情",
                   ["行情", "查询", "股价", "多少钱", "涨跌", "走势", "分析"],
                   _handler_stock_lookup, priority=8, requires=["trader"]),

        Capability("market_scan", "trading", "扫描全市场/自选股",
                   ["扫描", "市场", "大盘", "自选", "scan"],
                   _handler_scan_market, priority=7, requires=["trader"]),

        Capability("watchlist", "trading", "查看自选股列表",
                   ["自选股", "watchlist", "持仓列表"],
                   _handler_watchlist, priority=5, requires=["trader"]),

        Capability("auto_trade", "trading", "触发自主交易分析",
                   ["买入", "卖出", "买股", "卖股", "买进", "卖掉", "交易", "操盘", "下单", "买", "卖", "buy", "sell"],
                   _handler_trade, priority=9, requires=["trader", "brain"]),

        # ═══ 系统 ═══
        Capability("system_status", "system", "查看GBT系统状态",
                   ["系统状态", "运行状态", "GBT状态", "服务状态", "状态"],
                   _handler_system_status, priority=6, requires=["brain"]),

        Capability("watcher_check", "system", "守夜人安全监控",
                   ["监控状态", "安全监控", "守夜人", "安全检查", "watcher", "监控"],
                   _handler_watcher_check, priority=6, requires=["watcher"]),

        Capability("account_query", "system", "查看模拟账户",
                   ["账户", "资金", "余额", "盈亏", "持仓", "仓位", "钱"],
                   _handler_account, priority=6, requires=["account"]),

        # ═══ 通知 ═══
        Capability("notify", "notification", "发送Windows桌面通知",
                   ["通知", "提醒我", "提醒", "弹窗"],
                   _handler_notify, priority=4),

        # ═══ 编程/黑客 ═══
        Capability("web_search", "hacker", "网络搜索获取实时信息",
                   ["搜索", "查一下", "search", "百度", "谷歌"],
                   _handler_web_search, priority=9),

        Capability("file_operation", "hacker", "文件读写操作",
                   ["读文件", "写文件", "文件", "代码", "编辑"],
                   _handler_file_op, priority=6),

        Capability("code_exec", "hacker", "执行Python/Shell代码",
                   ["执行代码", "运行代码", "```", "shell", "cmd"],
                   _handler_code_exec, priority=8, requires=["desktop_ctl"]),

        # ═══ v3.0: 屏幕AI + 语音 + 精准抓取 + 操盘流水线 ═══
        Capability("screen_ocr", "desktop", "屏幕OCR识别桌面文字",
                   ["OCR", "识别屏幕", "看屏幕", "读屏幕", "屏幕文字", "识图"],
                   _handler_screen_ocr, priority=7),

        Capability("voice_speak", "notification", "Windows语音朗读输出",
                   ["说", "朗读", "语音", "讲话", "speak", "播报"],
                   _handler_voice_speak, priority=5),

        Capability("login_detect", "desktop", "OCR检测券商登录状态",
                   ["检测登录", "登录检测", "登录状态", "是否登录"],
                   _handler_login_detect, priority=8, requires=["desktop_ctl"]),

        Capability("precision_scrape", "hacker", "多源精准资讯抓取交叉验证",
                   ["抓取", "资讯", "新闻", "scrape", "行情快讯", "精准"],
                   _handler_precision_scrape, priority=10),

        Capability("auto_pipeline", "trading", "自主操盘流水线(开浏览器→检测登录→接手)",
                   ["操盘流水线", "自动操盘", "开始操盘", "自主交易", "自动交易"],
                   _handler_auto_pipeline, priority=10, requires=["trader", "brain"]),
    ]

    for cap in caps:
        router.register(cap)

    L.info(f"已注册 {len(caps)} 项能力到智能路由器")
    return len(caps)


# 自动注册
register_all()
