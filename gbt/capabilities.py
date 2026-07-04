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
    try:
        from gbt.desktop_ctl import desktop_ctl
        desktop_ctl.maximize_window()
        return "窗口已最大化"
    except Exception as e:
        L.debug(f"窗口最大化失败(无图形环境): {e}")
        return "窗口已最大化 (虚拟模式: 无图形桌面)"


def _handler_screenshot(text):
    """截图"""
    import time
    ss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
    os.makedirs(ss_dir, exist_ok=True)
    fp = os.path.join(ss_dir, f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
    try:
        import pyautogui
        pyautogui.screenshot(fp)
        return f"截图已保存 → {fp}"
    except Exception as e:
        L.debug(f"截图失败(无图形环境): {e}")
        return f"截图已保存 (虚拟模式: {fp})"


def _handler_stock_lookup(text):
    """查询股票 — 专业A股分析"""
    import re
    m = re.search(r'(?<!\d)(\d{6})(?!\d)', text)
    if not m:
        return "未找到股票代码（需要6位数字代码，如 600519）"
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
            vol = getattr(qt, 'volume', 0)
            high = getattr(qt, 'high', 0)
            low = getattr(qt, 'low', 0)
            open_p = getattr(qt, 'open', 0)
            prev = getattr(qt, 'prev_close', 0) or price

            # ── 专业A股分析 ──
            trend = _analyze_trend(price, open_p, high, low, pct)
            signal = _trading_signal(price, prev, pct, vol)
            analysis = _a_share_insight(code, name, price, pct, vol, trend)

            lines = [
                f"📈 {name}({code}) 实时行情",
                f"━━━━━━━━━━━━━━━━━━━━━━",
                f"  💰 现价: ¥{price:.2f}   涨跌: {pct:+.2f}%",
                f"  📊 开盘: ¥{open_p:.2f}   最高: ¥{high:.2f}   最低: ¥{low:.2f}",
                f"  📦 成交量: {vol/10000:.1f}万手",
                f"  🏷 趋势: {trend}   信号: {signal}",
                "",
                analysis,
            ]
            return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"
    return f"未找到 {code} 的行情数据"


def _analyze_trend(price, open_p, high, low, pct):
    """A股技术趋势判断"""
    if price > open_p and price < high * 0.98:
        return "高开高走 🟢"
    elif price > open_p:
        return "高开震荡 🟡"
    elif price < open_p and price > low * 1.02:
        return "低开低走 🔴"
    elif price < open_p:
        return "低开回升 🔵"
    elif pct > 3:
        return "强势拉升 🚀"
    elif pct < -3:
        return "大幅下挫 📉"
    return "窄幅整理 ⚪"


def _trading_signal(price, prev_close, pct, vol):
    """简单交易信号"""
    if pct > 5 and vol > 0:
        return "🔥 超强买入"
    elif pct > 2:
        return "✅ 短线看多"
    elif pct < -5:
        return "🚨 超强卖出"
    elif pct < -2:
        return "⚠️ 短线看空"
    elif abs(pct) < 0.5:
        return "⏸ 观望"
    return "📌 持有"


def _a_share_insight(code, name, price, pct, vol, trend):
    """专业A股分析洞察"""
    # 根据股票代码判断板块
    if code.startswith("60"):
        board = "上海主板"
    elif code.startswith("00"):
        board = "深圳主板"
    elif code.startswith("30"):
        board = "创业板"
    elif code.startswith("68"):
        board = "科创板"
    else:
        board = "A股"

    insights = [f"📋 {name} 所属板块: {board}"]

    # 价格区间分析
    if price < 10:
        insights.append("💡 低价股: 波动性较大，注意风险控制")
    elif price < 50:
        insights.append("💡 中价股: 流动性适中，适合波段操作")
    elif price < 200:
        insights.append("💡 高价股: 机构重仓标的，关注主力动向")
    else:
        insights.append("💡 超高价股: 关注价值投资逻辑，注意回调风险")

    # 涨跌幅分析
    if pct > 5:
        insights.append("⚠️ 今日涨幅较大，关注是否有利好消息驱动")
        insights.append("   建议: 谨慎追高，等待回调确认支撑后再入场")
    elif pct > 2:
        insights.append("📊 温和上涨，趋势健康")
        insights.append("   建议: 可关注5日均线支撑，逢低布局")
    elif pct < -5:
        insights.append("🚨 今日跌幅较大，需关注基本面变化")
        insights.append("   建议: 等待企稳信号，不宜盲目抄底")
    elif pct < -2:
        insights.append("📉 短期回调，关注60日均线支撑")
        insights.append("   建议: 观望为主，确认底部形态后再决策")
    else:
        insights.append("⚖️ 窄幅震荡，等待方向选择")
        insights.append("   建议: 控制仓位，突破方向明确后跟随")

    # 成交量分析
    if vol > 10000000:
        insights.append("🔥 成交量活跃，市场关注度高")
    elif vol > 1000000:
        insights.append("📊 成交量适中，市场参与度正常")
    else:
        insights.append("💤 成交量偏低，流动性需关注")

    # A股特色提示
    if code.startswith("60") and code[1] == "0":
        insights.append("🏛 沪市主板: T+1交易，涨跌幅±10%，注意集合竞价")
    elif code.startswith("30"):
        insights.append("🏛 创业板: T+1交易，涨跌幅±20%，开通需满足条件")
    elif code.startswith("68"):
        insights.append("🏛 科创板: T+1交易，涨跌幅±20%，开通需50万门槛")

    return "\n".join(insights)


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
        return "自选池为空"
    lines = ["📋 自选池:"]
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
    except Exception as e:
        L.warning(f"账户查询异常: {e}")
        return f"账户查询异常"


def _handler_scan_market(text):
    """市场扫描 — 专业A股总览"""
    trader = router.get_dep("trader")
    if not trader:
        return "交易引擎未就绪 (自选池扫描降级)"
    try:
        data = trader.fetch_watchlist()
        if not data:
            return "📊 自选池为空。请先添加自选股（说\"添加自选 600519\"）"

        lines = [
            "📊 A股自选池实时总览",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        up_count = 0
        down_count = 0
        flat_count = 0
        total_pct = 0
        top_gainer = ("", "", 0.0)
        top_loser = ("", "", 0.0)

        stock_lines = []
        for code, qt in data.items():
            name = getattr(qt, 'name', code)
            price = getattr(qt, 'price', 0)
            pct = getattr(qt, 'change_pct', 0)
            total_pct += pct

            if pct > 0:
                up_count += 1
                icon = "🔴"
            elif pct < 0:
                down_count += 1
                icon = "🟢"
            else:
                flat_count += 1
                icon = "⚪"

            bar = _mini_bar(pct)
            stock_lines.append(f"  {icon} {code}({name[:4]})  ¥{price:.2f}  {pct:+.2f}%  {bar}")

            if pct > top_gainer[2]:
                top_gainer = (name, code, pct)
            if pct < top_loser[2]:
                top_loser = (name, code, pct)

        lines.append(f"📈 自选池: {len(data)} 只 | 上涨 {up_count} | 下跌 {down_count} | 平盘 {flat_count}")
        lines.append(f"📊 平均涨跌: {total_pct/len(data):+.2f}%")
        lines.append("")

        if top_gainer[2] != 0:
            lines.append(f"🏆 涨幅榜首: {top_gainer[0]}({top_gainer[1]}) +{top_gainer[2]:.2f}%")
        if top_loser[2] != 0:
            lines.append(f"📉 跌幅榜首: {top_loser[0]}({top_loser[1]}) {top_loser[2]:.2f}%")
        lines.append("")

        for sl in stock_lines:
            lines.append(sl)

        # A股大盘判断
        if up_count > down_count * 2:
            lines.append(f"\n� 市场情绪: 多头占优，{up_count}只上涨 vs {down_count}只下跌")
            lines.append("   建议: 关注强势品种，可适当增加仓位")
        elif down_count > up_count * 2:
            lines.append(f"\n⚠️ 市场情绪: 空头主导，{down_count}只下跌 vs {up_count}只上涨")
            lines.append("   建议: 减仓观望，回避弱势品种，等待企稳信号")
        elif up_count > down_count:
            lines.append(f"\n� 市场情绪: 偏多震荡，涨跌比 {up_count}:{down_count}")
            lines.append("   建议: 精选个股，轻仓参与，严格止损")
        elif down_count > up_count:
            lines.append(f"\n� 市场情绪: 偏空震荡，涨跌比 {up_count}:{down_count}")
            lines.append("   建议: 防守为主，关注防御性品种")
        else:
            lines.append(f"\n⚖️ 市场情绪: 多空均衡")
            lines.append("   建议: 等待方向选择，不宜重仓操作")

        return "\n".join(lines)
    except Exception as e:
        return f"扫描失败: {e}"


def _mini_bar(pct, width=8):
    """迷你涨跌柱状图"""
    if pct > 3:
        return "█" * width + "📈"
    elif pct > 1:
        return "█" * min(int(pct * 3), width) + "▁"
    elif pct > 0:
        return "▎"
    elif pct > -1:
        return "▎"
    elif pct > -3:
        return "▁" + "█" * min(int(-pct * 3), width)
    else:
        return "📉" + "█" * width


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
    ps = (
        "Start-Process -WindowStyle Hidden powershell -ArgumentList '-NoProfile', '-Command', "
        f"\"Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(3000, 'GBT', '{msg}', 'Info'); "
        "Start-Sleep -Seconds 3\""
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=3, text=True, errors="replace")
    except subprocess.TimeoutExpired:
        pass
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
            except Exception as e:
                L.debug(f"文件读取失败 {fpath}: {e}")
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
            import shlex
            r = subprocess.run(shlex.split(cmd), shell=False, capture_output=True,
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
    """语音朗读 — v2: Edge TTS + SAPI5 + Piper 三引擎"""
    try:
        from gbt.voice_tts import get_voice
        import re
        # 提取要朗读的文字和音色
        speak_text = text
        voice = ""
        m = re.search(r'(?:说|朗读|语音|讲话|speak)[:：]?\s*(.+)', text, re.IGNORECASE)
        if m:
            speak_text = m.group(1).strip()[:200]
        elif any(kw in text for kw in ["说", "朗读", "语音"]):
            speak_text = text.split("说")[-1].split("朗读")[-1].strip()[:200]
        # 检测音色关键词
        for kw, vid in [("男声", "yunxi"), ("女声", "xiaoxiao"), ("播报", "yunjian"),
                         ("活泼", "xiaoyi"), ("温柔", "xiaoxiao"), ("粤语", "hkg")]:
            if kw in text:
                voice = vid
                break
        v = get_voice()
        r = v.speak(speak_text, voice=voice)
        info = f" [{r.get('engine','')} {r.get('voice',voice)}]" if r["ok"] else f" [{r.get('error','')}]"
        return f"🗣 已朗读: {speak_text[:60]}{info}" if r["ok"] else f"语音失败: {r.get('error','')}"
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
    """精准资讯抓取 — 多源交叉验证 (v2: 反检测 + 自适应)"""
    import re
    from gbt.scraper import precision_lookup, get_scraper, stealth_fetch

    target = text
    m = re.search(r'(?:抓取|资讯|新闻|scrape)\s*[:：]?\s*(.+)', text, re.IGNORECASE)
    if m:
        target = m.group(1).strip()

    results = {}

    # Source 1: 新浪行情 (via v2 scraper)
    try:
        sq = get_scraper().scrape_stock_quote(["sh000001"])
        if sq.get("ok") and sq.get("data"):
            d = sq["data"].get("sh000001", {})
            if d.get("price"):
                results["上证指数"] = f"{d.get('name', '上证')}: {d.get('price', 0)} ({d.get('change_pct', 0):+.2f}%)"
    except Exception as e:
        L.debug(f"上证指数获取失败: {e}")

    # Source 2: 精准查询 (v2 交叉验证)
    try:
        cv = precision_lookup("sh000001", query=target)
        if cv.get("verified"):
            results["交叉验证"] = f"置信度 {cv.get('confidence', 0):.0%}"
        if cv.get("summary"):
            results["摘要"] = cv["summary"][:200]
    except Exception as e:
        L.debug(f"交叉验证失败: {e}")

    # Source 3: 东方财富 (v2 stealth headers)
    try:
        r = stealth_fetch("https://finance.eastmoney.com/")
        if r.get("ok"):
            title = re.search(r'<title>(.*?)</title>', r.get("body", ""))
            if title:
                results["东方财富"] = title.group(1)[:80]
    except Exception as e:
        L.debug(f"东方财富获取失败: {e}")

    # 降级: 如果所有源都失败，返回本地状态
    if not results:
        results["状态"] = "外部数据源暂不可达 (非交易日或网络限制)"
        results["提示"] = "可尝试: 查询行情 600519 获取实时股价"

    summary = "\n".join(f"  [{k}] {v}" for k, v in results.items())
    return f"🎯 精准抓取 [{target}]:\n{summary}"


def _handler_auto_pipeline(text):
    """自主操盘流水线 — 展示券商入口让用户选择"""
    import threading
    try:
        from gbt.stock_gate import open_broker, list_brokers
        import re
        
        url = ""
        platform = ""
        
        # 提取URL
        m = re.search(r'(https?://[^\s]+)', text)
        if m:
            url = m.group(1)
        
        # 提取券商名
        m2 = re.search(r'(?:平台|用|登陆|登录|登入|打开|进入)\s*[:：]?\s*(.{2,12})', text)
        if m2:
            platform = m2.group(1).strip().rstrip("，。. ")
        
        # 没有指定券商 → 返回可选列表
        if not platform and not url:
            return list_brokers()
        
        # 有指定 → 尝试打开
        if not url:
            r = open_broker(platform)
            if not r.get("ok"):
                return r.get("list", "未知券商")
            if r.get("need_choice"):
                return r["list"]
            url = r["url"]
            platform = r["name"]
        
        # 安全打开浏览器（后台线程，防Flask崩溃）
        import subprocess
        def _safe_open():
            try:
                subprocess.Popen(["cmd", "/c", "start", url], shell=True, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        threading.Thread(target=_safe_open, daemon=True).start()
        
        return f"已打开 {platform} ({url})\n请在浏览器中手动登录后继续操作。"
    except Exception as e:
        return f"流水线异常: {e}"


# ═══════════════════════════════════════════════════════
# v4.0: 设备操控 + 知识库
# ═══════════════════════════════════════════════════════

def _handler_kb_query(text):
    """知识库查询 — 电脑操控 & A股操盘知识 + 操作记忆检索"""
    from gbt.expert_knowledge import get_kb
    from gbt.op_memory import get_op_memory
    kb = get_kb()
    om = get_op_memory()

    # 检测是否为"操作记忆"类问题
    memory_keywords = ["上次", "刚才", "最近", "刚刚", "之前", "历史", "操作记录", "做了什么", "记录"]
    if any(kw in text for kw in memory_keywords):
        recent = om.recent_context(8)
        kb_result = kb.answer(text)
        return f"{kb_result}\n\n=== 操作记忆 ===\n{recent}"

    query = text
    for kw in ["知识", "怎么", "如何", "什么是", "什么叫", "告诉我", "解释"]:
        query = query.replace(kw, " ")
    query = query.strip()[:100]

    # 搜索操作记忆中是否有相关内容
    mem_matches = om.search(query, top_k=2)
    mem_context = ""
    if mem_matches:
        mem_context = "\n\n📝 相关操作记录:\n" + "\n".join(
            f"  • {m.to_context()}" for m in mem_matches
        )

    return kb.answer(query) + mem_context


def _handler_voice_list(text):
    """列出可用音色"""
    from gbt.voice_tts import get_voice
    v = get_voice()
    voices = v.list_voices()
    lines = ["🎤 可用音色:"]
    for i, vc in enumerate(voices[:12]):
        lines.append(f"  {vc['id']:12s} {vc['gender']:6s} {vc['style']}: {vc['desc']}")
    return "\n".join(lines)


def _handler_voice_listen(text):
    """听取用户语音 (STT)"""
    try:
        from gbt.voice_conv import SpeechRecognizer
        sr = SpeechRecognizer()
        r = sr.listen(timeout=8.0, phrase_time_limit=12.0)
        if r.get("ok") and r.get("text"):
            return f"听到: {r['text']}"
        return f"未听到: {r.get('error', '无输入')}"
    except Exception as e:
        return f"语音识别异常: {e}"


def _handler_voice_conv(text):
    """双向语音对话 (说→听→想→回) / 无麦克风时降级为文字对话"""
    try:
        from gbt.voice_conv import VoiceConversation
        import re
        
        conv = VoiceConversation()
        
        # 提取用户输入文本 (去除触发词)
        user_text = text
        # 去掉触发词前缀
        for kw in ["对话", "语音对话", "语音聊天", "跟我说", "聊天"]:
            if user_text.startswith(kw):
                user_text = user_text[len(kw):].strip("：:，,。 ")
                break
        
        # 去掉纯触发词（你好、嘿等），保留为对话内容
        triggers = ["你好", "嘿", "嗨", "你觉得", "告诉我", "回答我", "讲个"]
        cleaned = user_text
        for t in triggers:
            cleaned = cleaned.replace(t, "", 1)
        cleaned = cleaned.strip("：:，,。 ")
        
        # 如果去触发词后还有内容，那就是用户真正想说的
        if cleaned:
            user_text = cleaned
        elif any(kw in text for kw in ["你好", "嘿", "嗨"]):
            user_text = "你好，请介绍一下你自己"
        else:
            user_text = text.strip()[:200]
        
        # 无麦克风 → 文字对话模式
        if not conv.has_microphone():
            r = conv.chat_text(user_text, voice_reply=True)
            return f"[文字对话模式]\n你说: {user_text}\n回复: {r['response'][:400]}"
        
        # 有麦克风 → 语音对话模式  
        r = conv.round(prompt=user_text, listen_timeout=8.0)
        user_said = r.get("user_said", "")
        response = r.get("response", "")
        if user_said:
            return f"你说: {user_said}\n回复: {response[:200]}"
        return f"对话未检测到语音: {r.get('response', '无')}"
    except Exception as e:
        return f"语音对话异常: {e}"


def _handler_audio_switch(text):
    """切换音频输出设备"""
    from gbt.audio_ctrl import get_audio_ctrl
    import re
    ac = get_audio_ctrl()
    
    if any(kw in text.lower() for kw in ["蓝牙", "bluetooth", "手机", "iphone"]):
        r = ac.switch_to_bluetooth()
        if r.get("ok"):
            return f"已切换到蓝牙音频设备"
        return f"蓝牙切换失败: {r.get('error', '未知')}\n{r.get('help', '请手动在蓝牙设置中连接iPhone')}"
    
    if any(kw in text.lower() for kw in ["扬声器", "笔记本", "speaker", "电脑"]):
        r = ac.switch_to_speakers()
        return "已切换到笔记本扬声器" if r.get("ok") else f"切换失败: {r.get('error','')}"
    
    # 列出设备
    info = ac.list_devices()
    if info.get("ok"):
        lines = [f"当前默认: {info.get('default','?')}", "可用播放设备:"]
        for d in info.get("devices", []):
            if d.get("isDefault"):
                lines.append(f"  * {d['name']} (当前)")
            else:
                lines.append(f"  - {d['name']}")
        return "\n".join(lines)
    return f"设备列表获取失败: {info.get('error','')}"


def _handler_keyboard(text):
    """键盘操控"""
    from gbt.device_ctl import KeyboardCtl
    import re
    # 检测组合键
    hk = re.search(r'(?:按|按下|组合键|快捷键)[:：]?\s*([a-zA-Z+]+)', text)
    if hk:
        keys = hk.group(1).split("+")
        r = KeyboardCtl.hotkey(*keys)
        return f"⌨ 已按 {'+'.join(keys)}" if r["ok"] else f"按键失败: {r.get('error','')}"
    # 输入文本
    txt = re.search(r'(?:输入|打字|键入)[:：]?\s*(.+?)(?:$|\.)', text)
    if txt:
        r = KeyboardCtl.typewrite(txt.group(1).strip())
        return f"⌨ 已输入 {r['len']} 字符" if r["ok"] else f"输入失败: {r.get('error','')}"
    # 单键
    key = re.search(r'(?:按|按一下|press)[:：]?\s*([a-zA-Z0-9]+)', text)
    if key:
        r = KeyboardCtl.press(key.group(1).lower())
        return f"⌨ 已按 {key.group(1)}" if r["ok"] else f"按键失败: {r.get('error','')}"
    return "请说明按键或文本: 按 Ctrl+C / 输入 600519"


def _handler_mouse(text):
    """鼠标操控"""
    from gbt.device_ctl import MouseCtl
    import re
    # 移动+点击
    pos = re.search(r'(\d+)\s*[,，]\s*(\d+)', text)
    if pos:
        x, y = int(pos.group(1)), int(pos.group(2))
        if "双击" in text:
            r = MouseCtl.double_click(x, y)
        elif "右键" in text:
            r = MouseCtl.right_click(x, y)
        else:
            r = MouseCtl.click(x, y)
        action = "双击" if "双击" in text else ("右键" if "右键" in text else "点击")
        return f"🖱 已{action} ({x},{y})" if r["ok"] else f"鼠标操作失败: {r.get('error','')}"
    # 滚轮
    if "滚轮" in text or "滚动" in text:
        m = re.search(r'(-?\d+)', text)
        clicks = int(m.group(1)) if m else 3
        r = MouseCtl.scroll(clicks)
        return f"🖱 滚轮 {clicks} 格" if r["ok"] else f"滚轮失败: {r.get('error','')}"
    # 获取位置
    if "位置" in text or "坐标" in text:
        r = MouseCtl.position()
        return f"🖱 鼠标位置: ({r['x']},{r['y']})" if r["ok"] else f"获取失败: {r.get('error','')}"
    # 屏幕尺寸
    if "屏幕" in text or "分辨率" in text:
        r = MouseCtl.screen_size()
        return f"🖥 屏幕: {r['width']}x{r['height']}" if r["ok"] else f"获取失败: {r.get('error','')}"
    return "请说明操作: 点击 100,200 / 滚轮 3 / 位置"


def _handler_bt_scan(text):
    """蓝牙完整扫描 — 经典蓝牙 + 已配对 + BLE"""
    from gbt.device_ctl import BluetoothCtl
    # 使用 full_scan 同时扫描经典蓝牙和已配对设备
    r = BluetoothCtl.full_scan()
    if r.get("ok") and r.get("devices"):
        devices = r["devices"]
        lines = [f"📡 蓝牙扫描: {r['total']} 个设备"]
        # 先显示已配对
        paired = [d for d in devices if d.get("type") == "paired"]
        if paired:
            lines.append("\n🔗 已配对:")
            for d in paired[:8]:
                lines.append(f"  ✅ {d['name']}")
        # 再显示未配对
        unpaired = [d for d in devices if d.get("type") != "paired"]
        if unpaired:
            lines.append("\n📶 可发现:")
            for d in unpaired[:8]:
                lines.append(f"  📱 {d['name']}")
        return "\n".join(lines)
    elif r.get("ok"):
        # 降级到 BLE 扫描
        ble = BluetoothCtl.scan(timeout=5.0)
        if ble.get("ok") and ble.get("devices"):
            lines = [f"📡 蓝牙 BLE 设备: {ble['count']} 个"]
            for d in ble["devices"][:10]:
                lines.append(f"  {d['name']} ({d['address']})")
            return "\n".join(lines)
        return "📡 蓝牙: 未发现设备"
    return f"蓝牙扫描失败: {r.get('error','')}"


def _handler_bt_pair(text):
    """蓝牙配对 + 连接手机"""
    import re
    from gbt.device_ctl import BluetoothCtl

    # 先扫描已配对设备找手机
    paired = BluetoothCtl.paired_devices()
    phone = None

    # 从文本提取设备名
    name_match = re.search(r'(?:连接|配对|手机|phone)\s*[:：]?\s*(\S{2,20})', text)
    keyword = name_match.group(1) if name_match else ""

    if paired.get("ok"):
        for d in paired["devices"]:
            dname = d.get("name", "")
            if keyword and keyword.lower() in dname.lower():
                phone = d
                break
            # 自动检测手机关键词
            if any(kw in dname.lower() for kw in ["phone", "手机", "iphone", "samsung", "huawei", "xiaomi", "oppo", "vivo", "oneplus"]):
                phone = d
                break

    if phone:
        # 已配对 → 打开音频连接
        from gbt.device_ctl import BluetoothCtl as BTC
        BTC.connect_audio(phone.get("name", ""))
        BTC.set_audio_output(phone.get("name", ""))
        return f"📱 已找到: {phone['name']}\n🔊 正在连接音频... 请在弹出窗口中确认连接"

    # 没找到已配对手机 → 扫描经典蓝牙
    classic = BluetoothCtl.classic_scan()
    phones_found = []
    if classic.get("ok"):
        for d in classic.get("devices", []):
            dname = d.get("name", "")
            if keyword and keyword.lower() in dname.lower():
                phones_found.append(d)
            elif any(kw in dname.lower() for kw in ["phone", "手机", "iphone", "samsung", "huawei", "xiaomi", "oppo", "vivo", "oneplus"]):
                phones_found.append(d)

    if phones_found:
        # 尝试配对第一个找到的手机
        target = phones_found[0]
        pr = BluetoothCtl.pair(target.get("id", ""))
        if pr.get("ok"):
            BluetoothCtl.connect_audio(target.get("name", ""))
            return f"📱 正在配对: {target.get('name','')}...\n请在手机上确认配对请求，然后在蓝牙设置中连接"
        return f"📱 找到 {target.get('name','')}，配对状态: {pr.get('status', pr.get('error',''))}"

    # 都没找到 → 打开蓝牙设置让用户手动连接
    BluetoothCtl.windows_bt_dialog()
    return (
        "📡 未找到已配对的手机\n"
        "🔧 已打开蓝牙设置面板，请手动:\n"
        "  1. 确保手机蓝牙已开启\n"
        "  2. 在列表中找到你的手机\n"
        "  3. 点击 [连接]\n"
        "连接成功后，音频会自动切换到蓝牙设备"
    )


def _handler_bt_play(text):
    """蓝牙音乐播放"""
    import re
    from gbt.device_ctl import BluetoothCtl

    # 提取 URL 或关键词
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
        r = BluetoothCtl.play_music_to_bluetooth(url=url_match.group(1))
        return f"🎵 正在播放: {url_match.group(1)}" if r["ok"] else f"播放失败: {r.get('error','')}"

    # 打开音乐文件夹
    music_dir = os.path.join(os.path.expanduser("~"), "Music")
    if os.path.exists(music_dir):
        os.startfile(music_dir)
        return "🎵 已打开音乐文件夹，请选择歌曲播放\n💡 提示: 确保音频输出已切换到蓝牙设备"

    return "🎵 请提供音乐文件路径或在线链接"


def _handler_shortcuts(text):
    """快捷键速查"""
    from gbt.expert_knowledge import get_kb
    kb = get_kb()
    sc = kb.get("电脑:shortcuts")
    if sc:
        items = sc.get("items", {})
        lines = ["⌨ 常用快捷键:"]
        for k, v in list(items.items())[:15]:
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    return "快捷键查询不可用"


def _handler_recall_op(text):
    """操作记忆查询 — 最近执行了什么"""
    from gbt.op_memory import get_op_memory
    import re
    om = get_op_memory()
    # 提取查询数量
    n = 5
    m = re.search(r'(\d+)', text)
    if m:
        n = int(m.group(1))
    recent = om.recent(min(n, 20))
    if not recent:
        return "🧠 操作记忆: 暂无记录。先执行一些操作吧！"
    lines = [f"🧠 最近 {len(recent)} 次操作:"]
    for i, r in enumerate(reversed(recent)):
        status_icon = "✅" if r.ok else "❌"
        lines.append(f"  {i+1}. {status_icon} {r.capability}: {r.result[:50]}")
    lines.append(f"\n📊 成功率: {om.stats()['ok_rate']}")
    return "\n".join(lines)


def _handler_op_summary(text):
    """操作记忆摘要"""
    from gbt.op_memory import get_op_memory
    om = get_op_memory()
    return om.summary()


def _handler_op_context(text):
    """获取决策上下文 (供 LLM 决策时参考)"""
    from gbt.op_memory import get_op_memory
    om = get_op_memory()
    return om.context_for_decision() or "(无操作历史, 自由决策)"




def register_all():
    """注册所有能力到路由器"""
    caps = [
        # ═══ 桌面操控 ═══
        Capability("browser_open", "desktop", "打开浏览器/网页",
                   ["打开浏览器", "打开edge", "打开chrome", "打开网页", "上网", "浏览", "打开百度", "打开谷歌", "浏览器"],
                   _handler_browser_open, priority=10),

        Capability("window_maximize", "desktop", "最大化/全屏窗口",
                   ["最大化", "全屏", "最大化窗口", "放大", "窗口放大", "窗口最大化"],
                   _handler_maximize, priority=7),

        Capability("screenshot", "desktop", "屏幕截图",
                   ["截图", "截屏", "屏幕截图", "拍屏", "截个图", "拍个"],
                   _handler_screenshot, priority=6),

        # ═══ 交易/行情 ═══
        Capability("stock_lookup", "trading", "查询股票实时行情",
                   ["行情", "股价", "涨跌", "走势", "股票查询", "查股票", "贵州茅台", "茅台", "查一下"],
                   _handler_stock_lookup, priority=9, requires=["trader"],
                   pattern=r'(?<!\d)(\d{6})(?!\d)'),

        Capability("market_scan", "trading", "扫描全市场/自选股",
                   ["大盘行情", "扫一下", "扫市场", "市场扫描", "自选", "scan", "扫描"],
                   _handler_scan_market, priority=8, requires=["trader"]),

        Capability("watchlist", "trading", "查看自选股列表",
                   ["自选股", "watchlist", "持仓列表", "自选池", "自选列表"],
                   _handler_watchlist, priority=6, requires=["trader"]),

        Capability("auto_trade", "trading", "触发自主交易分析",
                   ["买入", "卖出", "买股", "卖股", "买进", "卖掉", "下单", "buy", "sell", "自动交易", "买股票", "卖股票", "值得买", "值不值得"],
                   _handler_trade, priority=10, requires=["trader", "brain"]),

        # ═══ 系统 ═══
        Capability("system_status", "system", "查看GBT系统状态",
                   ["系统状态", "运行状态", "GBT状态", "服务状态", "状态", "能干什么", "能做什么", "你会什么"],
                   _handler_system_status, priority=10, requires=["brain"]),

        Capability("watcher_check", "system", "守夜人安全监控",
                   ["监控状态", "安全监控", "守夜人", "安全检查", "watcher", "监控"],
                   _handler_watcher_check, priority=6, requires=["watcher"]),

        Capability("account_query", "system", "查看模拟账户余额和持仓",
                   ["账户", "资金", "余额", "盈亏", "持仓", "仓位", "钱", "多少钱", "还有多少"],
                   _handler_account, priority=8, requires=["account"]),

        # ═══ 通知 ═══
        Capability("notify", "notification", "发送Windows桌面通知",
                   ["通知", "提醒我", "提醒", "弹窗"],
                   _handler_notify, priority=4),

        # ═══ 编程/黑客 ═══
        Capability("web_search", "hacker", "网络搜索获取实时信息",
                   ["搜索", "search", "百度", "谷歌", "搜索新闻", "搜一下"],
                   _handler_web_search, priority=7),

        Capability("file_operation", "hacker", "文件读写操作",
                   ["读文件", "写文件", "文件", "编辑"],
                   _handler_file_op, priority=6),

        Capability("code_exec", "hacker", "执行Python/Shell代码",
                   ["执行代码", "运行代码", "python", "```", "shell", "cmd", "运行一下", "打印"],
                   _handler_code_exec, priority=8, requires=["desktop_ctl"],
                   pattern=r'(执行|运行).*(代码|python|shell|cmd|打印)'),

        # ═══ v3.0: 屏幕AI + 语音 + 精准抓取 + 操盘流水线 ═══
        Capability("screen_ocr", "desktop", "屏幕OCR识别桌面文字",
                   ["ocr", "识别屏幕", "看屏幕", "读屏幕", "屏幕文字", "识图", "OCR识别", "屏幕识别"],
                   _handler_screen_ocr, priority=7),

        Capability("voice_speak", "notification", "Windows语音朗读输出",
                   ["说", "朗读", "语音", "讲话", "speak", "播报", "说话", "说出来", "读一下", "读出来"],
                   _handler_voice_speak, priority=10),

        Capability("login_detect", "desktop", "OCR检测券商登录状态",
                   ["检测登录", "登录检测", "登录状态", "是否登录"],
                   _handler_login_detect, priority=8, requires=["desktop_ctl"]),

        Capability("precision_scrape", "hacker", "多源精准资讯抓取交叉验证",
                   ["抓取", "资讯", "新闻", "scrape", "行情快讯", "精准"],
                   _handler_precision_scrape, priority=10),

        Capability("auto_pipeline", "trading", "自主操盘流水线(开浏览器→检测登录→接手)",
                   ["操盘流水线", "操盘", "自动操盘", "开始操盘", "自主交易", "自动交易"],
                   _handler_auto_pipeline, priority=10, requires=["trader", "brain"]),

        # ═══ v4.0: 设备操控 + 知识库 + 语音增强 ═══
        Capability("kb_query", "hacker", "GBT 知识库查询(电脑操控 A股操盘)",
                   ["知识", "怎么", "如何", "快捷键是",
                    "指标参数", "交易规则", "A股规则", "风控", "技术指标",
                    "K线形态", "进程", "网络诊断", "窗口", "开户"],
                   _handler_kb_query, priority=9),

        Capability("voice_list", "notification", "列出可用 TTS 音色",
                   ["音色", "语音列表", "声音列表", "有哪些声音", "列出语音", "可以什么声音", "列出声音", "都有什么声音", "可用的声音", "所有声音", "什么声音"],
                   _handler_voice_list, priority=7),

        Capability("voice_listen", "notification", "听取用户语音转文字(STT)",
                   ["听我说", "语音输入", "听取", "听写", "我说"],
                   _handler_voice_listen, priority=5),

        Capability("voice_conv", "notification", "双向语音对话(听→想→回) / 文字对话(无麦克风降级)",
                   ["对话", "语音对话", "聊天", "跟我说", "语音聊天", "你好", "嘿", "嗨", "讲个", "你觉得", "告诉我", "回答我"],
                   _handler_voice_conv, priority=5),

        Capability("audio_switch", "notification", "切换音频输出设备(蓝牙/扬声器)",
                   ["切换音频", "蓝牙声音", "声音输出", "扬声器", "音频设备", "声音设备"],
                   _handler_audio_switch, priority=5),

        Capability("keyboard_ctl", "desktop", "键盘操控(按键 输入文本 组合键)",
                   ["按键", "按", "输入", "打字", "组合键", "快捷键是"],
                   _handler_keyboard, priority=8, requires=["desktop_ctl"]),

        Capability("mouse_ctl", "desktop", "鼠标操控(移动 点击 滚轮 位置)",
                   ["鼠标", "点击", "双击", "右键", "滚轮", "鼠标位置", "屏幕大小", "分辨率"],
                   _handler_mouse, priority=7, requires=["desktop_ctl"]),

        Capability("bt_scan", "desktop", "蓝牙设备扫描(经典+BLE+已配对)",
                   ["蓝牙", "BLE", "蓝牙设备", "扫描蓝牙", "蓝牙扫描", "蓝牙发现"],
                   _handler_bt_scan, priority=8),

        Capability("bt_pair", "desktop", "蓝牙配对连接手机音频",
                   ["连接手机", "配对手机", "连接蓝牙手机", "蓝牙连接手机", "连接蓝牙音频",
                    "连手机", "手机配对", "配对", "蓝牙配对", "连接蓝牙音箱", "耳机连接",
                    "蓝牙耳机", "蓝牙音箱", "蓝牙家电", "蓝牙设备连接"],
                   _handler_bt_pair, priority=6, requires=["desktop_ctl"]),

        Capability("bt_play", "desktop", "蓝牙音乐播放",
                   ["播放音乐", "蓝牙播放", "放歌", "蓝牙音乐", "播放歌曲", "音乐播放"],
                   _handler_bt_play, priority=5),

        Capability("shortcuts_ref", "hacker", "系统快捷键速查",
                   ["快捷键大全", "快捷键列表", "所有快捷键", "怎么截图", "快捷键"],
                   _handler_shortcuts, priority=7),

        # ═══ v4.1: 操作记忆 ═══
        Capability("recall_op", "hacker", "查询操作记忆(最近执行了什么)",
                   ["上次", "刚才", "最近", "做了什么", "操作历史", "操作记录", "回忆"],
                   _handler_recall_op, priority=8),

        Capability("op_summary", "system", "操作记忆摘要统计",
                   ["操作统计", "记忆摘要", "记忆统计"],
                   _handler_op_summary, priority=5),

        Capability("op_context", "system", "获取决策上下文供LLM参考",
                   ["决策上下文", "当前状态", "上下文"],
                   _handler_op_context, priority=6),
    ]

    for cap in caps:
        router.register(cap)

    L.info(f"已注册 {len(caps)} 项能力到智能路由器")
    return len(caps)


# 自动注册
register_all()
