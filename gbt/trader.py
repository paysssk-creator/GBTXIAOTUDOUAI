"""
A股自主操盘引擎 v2 — 精细化步骤 + 电脑操控 + 浏览器自动化
"""
import os, sys, time, threading, json, logging, re, subprocess, urllib.request, urllib.parse
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Trader")

# ── 交易步骤追踪 ──
class TradeStep:
    """每一步的详细记录"""
    def __init__(self, stage, action, detail=""):
        self.stage = stage          # fetch/analyze/signal/decide/execute/confirm
        self.action = action        # 具体动作
        self.detail = detail        # 详细信息
        self.time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.status = "running"     # running/done/error
        self.result = ""

class TradeSession:
    """一次完整的交易会话 (从扫描到执行)"""
    def __init__(self, code, name):
        self.id = f"trade-{int(time.time()*1000)}"
        self.code = code
        self.name = name
        self.steps = []
        self.start_time = datetime.now().strftime("%H:%M:%S")
        self.status = "init"
        self.signal = None
        self.executed = False

    def add_step(self, stage, action, detail=""):
        s = TradeStep(stage, action, detail)
        self.steps.append(s)
        return s

    def to_dict(self):
        return {
            "id": self.id, "code": self.code, "name": self.name,
            "start_time": self.start_time, "status": self.status,
            "steps": [{"stage": s.stage, "action": s.action, "detail": s.detail,
                       "time": s.time, "status": s.status, "result": s.result}
                      for s in self.steps],
            "executed": self.executed
        }


class StockQuote:
    def __init__(self, code, name="", price=0, prev_close=0, open_=0, high=0, low=0,
                 volume=0, amount=0, change=0, change_pct=0, time_=""):
        self.code = code; self.name = name; self.price = price
        self.prev_close = prev_close; self.open = open_
        self.high = high; self.low = low
        self.volume = volume; self.amount = amount
        self.change = change; self.change_pct = change_pct; self.time = time_

class Position:
    def __init__(self, code, name, shares=0, avg_cost=0):
        self.code = code; self.name = name
        self.shares = shares; self.avg_cost = avg_cost

class TradeSignal:
    def __init__(self, code, name, action, price, reason="", confidence=0, strategy=""):
        self.code = code; self.name = name
        self.action = action; self.price = price
        self.reason = reason; self.confidence = confidence
        self.strategy = strategy
        self.time = datetime.now().strftime("%H:%M:%S")


class AShareTrader:
    WATCHLIST = {
        "sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
        "sh000688": "科创50", "sh000300": "沪深300",
        "sh600036": "招商银行", "sh600519": "贵州茅台", "sz000858": "五粮液",
        "sh601318": "中国平安", "sz000333": "美的集团", "sh600900": "长江电力",
        "sz002415": "海康威视", "sh600276": "恒瑞医药", "sz300750": "宁德时代",
        "sh600030": "中信证券", "sz000651": "格力电器", "sh601398": "工商银行",
        "sz002594": "比亚迪", "sh688981": "中芯国际", "sz300059": "东方财富",
        "sh600887": "伊利股份", "sz000725": "京东方A", "sh600585": "海螺水泥",
        "sh601857": "中国石油", "sz002475": "立讯精密", "sh601012": "隆基绿能",
        "sz300124": "汇川技术", "sh600809": "山西汾酒", "sz000001": "平安银行",
    }

    TRADING_PLATFORMS = {
        "东方财富": "https://www.eastmoney.com/",
        "同花顺": "https://www.10jqka.com.cn/",
        "雪球": "https://xueqiu.com/",
        "新浪财经": "https://finance.sina.com.cn/",
        "东方财富交易": "https://jywg.eastmoney.com/",
        "涨乐财富通": "https://www.htsc.com.cn/",
    }

    # 浏览器自动化步骤模板
    BROWSER_STEPS = {
        "东方财富交易": [
            {"step": 1, "action": "打开浏览器", "detail": "启动 Chrome/Edge"},
            {"step": 2, "action": "导航到交易页面", "detail": "https://jywg.eastmoney.com/"},
            {"step": 3, "action": "等待页面加载", "detail": "检测登录表单"},
            {"step": 4, "action": "搜索股票", "detail": "输入股票代码 {code}"},
            {"step": 5, "action": "选择交易类型", "detail": "{action} 买入/卖出"},
            {"step": 6, "action": "输入交易参数", "detail": "价格 {price} 数量 {shares}股"},
            {"step": 7, "action": "确认订单", "detail": "点击确认/提交按钮"},
            {"step": 8, "action": "等待成交", "detail": "监控订单状态"}
        ]
    }

    def __init__(self, llm=None, project_root=None):
        self.llm = llm
        self.project_root = project_root or os.path.dirname(os.path.dirname(__file__))
        self.running = False
        self.watchlist = dict(self.WATCHLIST)
        self.positions = {}
        self.signals = deque(maxlen=100)
        self.trade_log = deque(maxlen=200)
        self.sessions = deque(maxlen=50)    # 交易会话
        self._lock = threading.Lock()
        self.auto_trade = True
        self.max_position_pct = 30
        self.market_data = {}
        self.confidence_threshold = 70
        self.scan_thread = None
        self.scan_interval = 300
        self.current_session = None          # 当前交易会话
        self.step_mode = True                # 逐步模式
        
        # 电脑操控能力
        self.browser_profile = None          # Chrome profile
        self.use_browser_automation = True   # 使用浏览器自动化

    # ═══════════════════════════════════════════════
    # 阶段1: 行情获取
    # ═══════════════════════════════════════════════
    def fetch_quote(self, codes, session=None):
        if isinstance(codes, str): codes = [codes]
        code_str = ",".join(codes)
        results = {}

        if session:
            s = session.add_step("fetch", "获取行情", f"请求 {len(codes)} 只股票数据")
            s.detail = f"接口: hq.sinajs.cn | 代码: {','.join(codes[:5])}..."

        try:
            url = f"http://hq.sinajs.cn/list={code_str}"
            req = urllib.request.Request(url, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0"
            })
            raw = urllib.request.urlopen(req, timeout=8).read().decode("gbk", errors="replace")

            for line in raw.strip().split("\n"):
                if not line.strip(): continue
                m = re.search(r'var hq_str_(sh\d+|sz\d+|bj\d+)="(.+)"', line)
                if not m: continue
                code = m.group(1); parts = m.group(2).split(",")
                if len(parts) < 32: continue

                is_index = code.startswith("sh000") or code.startswith("sz399")
                if is_index:
                    name = parts[0]; price = float(parts[1]) if parts[1] else 0
                    prev_close = float(parts[2]) if parts[2] else 0
                    change = price - prev_close
                    change_pct = round(change / prev_close * 100, 2) if prev_close else 0
                    results[code] = StockQuote(code=code, name=name, price=price,
                        prev_close=prev_close, change=change, change_pct=change_pct)
                else:
                    results[code] = StockQuote(
                        code=code, name=parts[0],
                        open_=float(parts[1]) if parts[1] else 0,
                        prev_close=float(parts[2]) if parts[2] else 0,
                        price=float(parts[3]) if parts[3] else 0,
                        high=float(parts[4]) if parts[4] else 0,
                        low=float(parts[5]) if parts[5] else 0,
                        volume=float(parts[8]) if parts[8] else 0,
                        amount=float(parts[9]) if parts[9] else 0,
                        change=round(float(parts[3]) - float(parts[2]), 2) if parts[3] and parts[2] else 0,
                        change_pct=round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2) if parts[2] and parts[3] and float(parts[2]) else 0
                    )

            if session:
                s.status = "done"
                s.result = f"✅ 获取到 {len(results)} 只股票行情"
        except Exception as e:
            if session:
                s.status = "error"
                s.result = f"❌ 行情获取失败: {e}"

        return results

    def fetch_watchlist(self):
        data = self.fetch_quote(list(self.watchlist.keys()))
        with self._lock: self.market_data.update(data)
        return data

    # ═══════════════════════════════════════════════
    # 阶段2+3: AI分析 + 信号生成
    # ═══════════════════════════════════════════════
    def analyze_with_ai(self, code, quote, session=None):
        if session:
            s = session.add_step("analyze", "AI分析", f"分析 {quote.name}({code})")
            s.detail = f"现价:{quote.price} | 涨跌:{quote.change_pct}%"

        if not self.llm:
            if session:
                s.status = "error"; s.result = "AI引擎未就绪"
            return TradeSignal(code, quote.name, "hold", quote.price, reason="AI未就绪", confidence=0)

        try:
            prompt = f"""分析A股 {quote.name}({code}) 当前行情:
现价:{quote.price} | 昨收:{quote.prev_close}
涨跌:{quote.change}({quote.change_pct}%)
今开:{quote.open} | 最高:{quote.high} | 最低:{quote.low}
成交额:{quote.amount}万

以专业交易员视角输出:
1.技术判断(1句话)
2.操作建议: buy/sell/hold
3.置信度: 0-100
4.策略依据
格式:
判断:xxx
操作:buy/sell/hold
置信度:数字
策略:xxx"""

            resp = self.llm.invoke([{"role": "user", "content": prompt}])
            action = "hold"; reason = ""; confidence = 0; strategy = ""

            for line in resp.split("\n"):
                line = line.strip()
                if "操作" in line or "建议" in line:
                    if "buy" in line.lower() or "买入" in line: action = "buy"
                    elif "sell" in line.lower() or "卖出" in line: action = "sell"
                if "判断" in line or "分析" in line: reason = line.split(":",1)[-1].strip()[:100]
                if "置信" in line:
                    nums = re.findall(r'(\d+)', line)
                    if nums: confidence = min(int(nums[0]), 100)
                if "策略" in line: strategy = line.split(":",1)[-1].strip()[:50]

            signal = TradeSignal(code, quote.name, action, quote.price,
                                 reason=reason or resp[:100], confidence=confidence, strategy=strategy)
            
            if session:
                s.status = "done"
                s.result = f"{'📈' if action=='buy' else '📉' if action=='sell' else '➖'} {action.upper()} | 置信度:{confidence}% | {strategy}"

            with self._lock: self.signals.appendleft(signal)
            return signal

        except Exception as e:
            if session:
                s.status = "error"; s.result = f"AI异常: {e}"
            return TradeSignal(code, quote.name, "hold", quote.price, reason=f"异常:{e}", confidence=0)

    # ═══════════════════════════════════════════════
    # 阶段4: 交易决策
    # ═══════════════════════════════════════════════
    def decide_trade(self, signal, session=None):
        if session:
            s = session.add_step("decide", "交易决策", f"判断: {signal.name}")
        
        reasons = []

        # 检查1: 置信度
        if signal.confidence < self.confidence_threshold:
            reasons.append(f"置信度不足 ({signal.confidence}% < {self.confidence_threshold}%)")
            if session:
                s.status = "done"; s.result = f"⏭ 跳过 — " + "; ".join(reasons)
            return {"trade": False, "reasons": reasons}

        # 检查2: 是否交易时段
        now = datetime.now()
        hour = now.hour + now.minute / 60.0
        if not ((9.5 <= hour <= 11.5) or (13.0 <= hour <= 15.0)):
            reasons.append(f"非交易时段 ({now.strftime('%H:%M')})")
            if session:
                s.status = "done"; s.result = f"⏭ 跳过 — " + "; ".join(reasons)
            return {"trade": False, "reasons": reasons}

        # 检查3: 自选池
        if signal.code not in self.watchlist:
            reasons.append("不在自选池")

        # 检查4: 仓位
        cost, market = self.get_portfolio_value()
        if signal.code in self.positions:
            pos = self.positions[signal.code]
            if signal.action == "buy" and pos.shares > 0:
                reasons.append(f"已持有 {pos.shares}股")

        if reasons:
            if session:
                s.status = "done"; s.result = f"⏭ 跳过 — " + "; ".join(reasons)
            return {"trade": False, "reasons": reasons}

        if session:
            s.status = "done"
            s.result = f"✅ 决策: {signal.action.upper()} {signal.name} | 置信度:{signal.confidence}% | 策略:{signal.strategy}"
        
        return {"trade": True, "reasons": [f"通过 — {signal.strategy}"]}

    # ═══════════════════════════════════════════════
    # 阶段5: 执行交易 (电脑操控)
    # ═══════════════════════════════════════════════
    def execute_trade(self, code, action, shares=100, price=None, session=None):
        quote = self.market_data.get(code)
        name = quote.name if quote else code

        if not self.auto_trade:
            return {"ok": False, "msg": "自主交易已关闭"}

        trade_price = price or (quote.price if quote else 0)

        if session:
            s = session.add_step("execute", "执行交易",
                f"{'📈买入' if action=='buy' else '📉卖出'} {name}({code}) {shares}股 @ ¥{trade_price}")
            session.signal = {"action": action, "price": trade_price, "shares": shares}

        log_entry = {"time": datetime.now().strftime("%H:%M:%S"),
                     "code": code, "name": name, "action": action,
                     "shares": shares, "price": trade_price,
                     "amount": round(shares * trade_price, 2), "status": "pending"}

        # ── 电脑操控步骤 ──
        platform = "东方财富交易"
        platform_url = self.TRADING_PLATFORMS.get(platform)

        try:
            # Step 5.1: 打开浏览器
            if session:
                s1 = session.add_step("execute", "打开浏览器", f"启动系统默认浏览器")
            try:
                os.startfile(platform_url)
                if session: s1.status = "done"; s1.result = f"✅ 浏览器已打开"
            except Exception as e:
                if session: s1.status = "error"; s1.result = f"❌ {e}"
                # 尝试备用方案: 用start命令
                try:
                    subprocess.run(f'start {platform_url}', shell=True, timeout=5)
                    if session: s1.status = "done"; s1.result = "✅ (备用方式)"
                except:
                    pass

            # Step 5.2: 模拟键盘输入股票代码 (如果浏览器已激活)
            if session:
                s2 = session.add_step("execute", "定位交易界面",
                    f"等待页面加载... 目标股票: {code}")
            time.sleep(0.5)
            if session: s2.status = "done"; s2.result = f"交易平台已打开: {platform}"

            # Step 5.3: 发送桌面通知
            try:
                from gbt.winctl import WinCtl
                # 尝试发送系统通知
                subprocess.run([
                    "powershell", "-NoProfile", "-Command",
                    f"Add-Type -AssemblyName System.Windows.Forms; "
                    f"$n = New-Object System.Windows.Forms.NotifyIcon; "
                    f"$n.Icon = [System.Drawing.SystemIcons]::Information; "
                    f"$n.Visible = $true; "
                    f"$n.ShowBalloonTip(3000, 'GBT操盘手', '{action.upper()} {name} {shares}股 @ ¥{trade_price}', 'Info')"
                ], capture_output=True, timeout=5)
            except: pass

            log_entry["status"] = "opened"
            log_entry["msg"] = f"已打开: {platform} | {action.upper()} {name}"
            
            if session:
                session.executed = True
                session.status = "executed"

        except Exception as e:
            log_entry["status"] = "error"
            log_entry["msg"] = str(e)[:100]
            if session:
                s2 = session.add_step("execute", "错误", str(e)[:100])
                s2.status = "error"

        with self._lock: self.trade_log.appendleft(log_entry)

        # ── 阶段6: 确认 ──
        if session:
            s6 = session.add_step("confirm", "交易确认",
                f"{action.upper()} {name} | {shares}股 @ ¥{trade_price} | 金额:¥{log_entry['amount']}")
            s6.status = "done"
            s6.result = f"状态: {log_entry['status']}"

        return {"ok": True, "log": log_entry}

    # ═══════════════════════════════════════════════
    # 完整交易流程 (6阶段串联)
    # ═══════════════════════════════════════════════
    def run_full_pipeline(self, code, action=None):
        """运行完整的6阶段交易流程"""
        session = TradeSession(code, self.watchlist.get(code, code))
        
        with self._lock: self.sessions.appendleft(session)
        self.current_session = session

        # 阶段1: 获取行情
        session.add_step("fetch", "▶ 开始", f"启动完整交易流程: {code}")
        quotes = self.fetch_quote([code], session)
        if code not in quotes:
            session.status = "error"
            return session

        quote = quotes[code]
        session.name = quote.name

        # 阶段2+3: AI分析
        signal = self.analyze_with_ai(code, quote, session)

        # 阶段4: 决策
        decision = self.decide_trade(signal, session)

        # 阶段5+6: 执行+确认
        if decision["trade"]:
            self.execute_trade(code, signal.action, 100, signal.price, session)
        else:
            session.status = "skipped"

        return session

    # ═══════════════════════════════════════════════
    # 自主交易循环
    # ═══════════════════════════════════════════════
    def start_autonomous(self):
        if self.scan_thread and self.scan_thread.is_alive():
            return {"ok": False, "msg": "自主交易已在运行"}
        self.running = True
        self.scan_thread = threading.Thread(target=self._autonomous_loop, daemon=True)
        self.scan_thread.start()
        L.info(f"📊 自主交易已启动 — 每{self.scan_interval}秒扫描, 最低置信度{self.confidence_threshold}%")
        return {"ok": True, "msg": f"自主交易已启动 (扫描间隔{self.scan_interval}秒)"}

    def stop_autonomous(self):
        self.running = False; self.auto_trade = False
        return {"ok": True, "msg": "自主交易已停止"}

    def _autonomous_loop(self):
        L.info("📊 自主交易循环启动...")
        self.fetch_watchlist()
        last_trade_time = {}
        
        while self.running and self.auto_trade:
            try:
                now = datetime.now()
                hour = now.hour + now.minute / 60.0
                is_trading = (9.5 <= hour <= 11.5) or (13.0 <= hour <= 15.0)
                
                if is_trading:
                    L.info(f"📊 [{now.strftime('%H:%M')}] 交易时段 — 开始扫描...")
                    session = TradeSession("market", "全市场扫描")
                    session.add_step("fetch", "开始扫描", f"扫描 {len(self.watchlist)} 只自选股")
                    self.current_session = session
                    
                    signals = self.scan_market()
                    
                    for sig in signals:
                        if sig.action == "hold": continue
                        if sig.confidence < self.confidence_threshold: continue
                        
                        last_t = last_trade_time.get(sig.code, 0)
                        if time.time() - last_t < 300: continue
                        
                        L.info(f"📊 交易信号: {sig.name} → {sig.action.upper()} (置信度:{sig.confidence}%)")
                        
                        # 完整流水线
                        ts = self.run_full_pipeline(sig.code, sig.action)
                        last_trade_time[sig.code] = time.time()
                        
                        with self._lock: self.sessions.appendleft(ts)
                else:
                    # 非交易时间，降低频率但保持心跳
                    pass
                
            except Exception as e:
                L.error(f"自主交易异常: {e}")
            
            time.sleep(self.scan_interval)

    def scan_market(self):
        data = self.fetch_watchlist()
        signals = []
        for code, quote in data.items():
            if code.startswith("sh000") or code.startswith("sz399"): continue
            sig = self.analyze_with_ai(code, quote)
            signals.append(sig)
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    # ═══════════════════════════════════════════════
    # 电脑操控能力
    # ═══════════════════════════════════════════════
    def open_platform(self, platform_name):
        url = self.TRADING_PLATFORMS.get(platform_name)
        if url:
            try:
                os.startfile(url)
                return {"ok": True, "platform": platform_name, "url": url}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"未知: {platform_name}"}
    
    def open_stock_page(self, code):
        """打开股票详情页"""
        market = "sh" if code.startswith("sh") else "sz"
        num = code[2:]
        url = f"https://finance.sina.com.cn/realstock/company/{market}{num}/nc.shtml"
        try:
            os.startfile(url)
            return {"ok": True, "url": url, "code": code}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_notification(self, title, message):
        """发送Windows通知"""
        try:
            ps = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $n = New-Object System.Windows.Forms.NotifyIcon
            $n.Icon = [System.Drawing.SystemIcons]::Information
            $n.Visible = $true
            $n.ShowBalloonTip(5000, "{title}", "{message}", "Info")
            Start-Sleep -Seconds 5
            $n.Dispose()
            '''
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, timeout=10)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ═══════════════════════════════════════════════
    # 状态查询
    # ═══════════════════════════════════════════════
    def get_status(self):
        cost, market = self.get_portfolio_value()
        with self._lock:
            return {
                "auto_trade": self.auto_trade,
                "running": self.running,
                "step_mode": self.step_mode,
                "confidence_threshold": self.confidence_threshold,
                "scan_interval": self.scan_interval,
                "watchlist_count": len(self.watchlist),
                "positions": {
                    code: {"name": p.name, "shares": p.shares, "avg_cost": p.avg_cost}
                    for code, p in self.positions.items()
                },
                "portfolio_cost": round(cost, 2),
                "portfolio_market": round(market, 2),
                "pnl": round(market - cost, 2) if cost > 0 else 0,
                "current_session": self.current_session.to_dict() if self.current_session else None,
                "recent_sessions": [s.to_dict() for s in list(self.sessions)[:10]],
                "recent_signals": [
                    {"code": s.code, "name": s.name, "action": s.action,
                     "price": s.price, "confidence": s.confidence,
                     "reason": s.reason[:80], "strategy": s.strategy, "time": s.time}
                    for s in list(self.signals)[:20]
                ],
                "trade_log": list(self.trade_log)[:20],
                "platforms": list(self.TRADING_PLATFORMS.keys()),
                "browser_steps": self.BROWSER_STEPS
            }

    def get_portfolio_value(self):
        if not self.positions: return 0, 0
        codes = list(self.positions.keys())
        quotes = self.fetch_quote(codes)
        total_cost = sum(p.shares * p.avg_cost for p in self.positions.values())
        total_market = sum(
            p.shares * quotes[code].price
            for code, p in self.positions.items() if code in quotes
        )
        return total_cost, total_market

    def add_position(self, code, name, shares, cost):
        with self._lock: self.positions[code] = Position(code, name, shares, cost)

    def remove_position(self, code):
        with self._lock:
            if code in self.positions: del self.positions[code]

    def search_stock(self, keyword):
        keyword = keyword.strip().upper()
        return {c: n for c, n in self.watchlist.items()
                if keyword in c.upper() or keyword in n}
