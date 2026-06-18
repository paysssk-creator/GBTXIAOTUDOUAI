"""
A股自主操盘引擎 — 实时行情 + AI策略分析 + 交易执行
"""
import os, sys, time, threading, json, logging, re, subprocess, urllib.request, urllib.parse
from datetime import datetime
from collections import deque

L = logging.getLogger("GBT.Trader")

class StockQuote:
    """股票实时行情"""
    def __init__(self, code, name="", price=0, prev_close=0, open_=0, high=0, low=0,
                 volume=0, amount=0, change=0, change_pct=0, time_=""):
        self.code = code
        self.name = name
        self.price = price
        self.prev_close = prev_close
        self.open = open_
        self.high = high
        self.low = low
        self.volume = volume
        self.amount = amount
        self.change = change
        self.change_pct = change_pct
        self.time = time_

class Position:
    """持仓记录"""
    def __init__(self, code, name, shares=0, avg_cost=0):
        self.code = code
        self.name = name
        self.shares = shares
        self.avg_cost = avg_cost

class TradeSignal:
    """AI生成的交易信号"""
    def __init__(self, code, name, action, price, reason="", confidence=0, strategy=""):
        self.code = code
        self.name = name
        self.action = action  # "buy" / "sell" / "hold"
        self.price = price
        self.reason = reason
        self.confidence = confidence
        self.strategy = strategy
        self.time = datetime.now().strftime("%H:%M:%S")

class AShareTrader:
    """A股操盘手"""

    # 常用股票池
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

    def __init__(self, llm=None, project_root=None):
        self.llm = llm
        self.project_root = project_root or os.path.dirname(os.path.dirname(__file__))
        self.running = False
        self.watchlist = dict(self.WATCHLIST)
        self.positions = {}  # code -> Position
        self.signals = deque(maxlen=100)
        self.trade_log = deque(maxlen=200)
        self._lock = threading.Lock()
        self.auto_trade = False  # 安全锁：默认关闭自主交易
        self.max_position_pct = 30  # 单只股票最大仓位30%
        self.market_data = {}  # code -> StockQuote

    # ── 行情获取 ──
    def fetch_quote(self, codes):
        """获取实时行情 (新浪接口)"""
        if isinstance(codes, str):
            codes = [codes]

        code_str = ",".join(codes)
        results = {}

        try:
            url = f"http://hq.sinajs.cn/list={code_str}"
            req = urllib.request.Request(url, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0"
            })
            raw = urllib.request.urlopen(req, timeout=8).read().decode("gbk", errors="replace")

            for line in raw.strip().split("\n"):
                if not line.strip():
                    continue
                m = re.search(r'var hq_str_(sh\d+|sz\d+|bj\d+)="(.+)"', line)
                if not m:
                    continue
                code = m.group(1)
                parts = m.group(2).split(",")
                if len(parts) < 32:
                    continue

                is_index = code.startswith("sh000") or code.startswith("sz399") or code.startswith("sz3990")

                if is_index:
                    # 指数格式: name,price,change,change%,volume,amount
                    name = parts[0]
                    price = float(parts[1]) if parts[1] else 0
                    prev_close = float(parts[2]) if parts[2] else 0
                    change = price - prev_close
                    change_pct = round(change / prev_close * 100, 2) if prev_close else 0
                    results[code] = StockQuote(
                        code=code, name=name, price=price, prev_close=prev_close,
                        change=change, change_pct=change_pct,
                        volume=float(parts[4]) if parts[4] else 0,
                        amount=float(parts[5]) if parts[5] else 0
                    )
                else:
                    # 个股格式: name,open,prev_close,price,high,low,...,date,time,...
                    name = parts[0]
                    open_ = float(parts[1]) if parts[1] else 0
                    prev_close = float(parts[2]) if parts[2] else 0
                    price = float(parts[3]) if parts[3] else 0
                    high = float(parts[4]) if parts[4] else 0
                    low = float(parts[5]) if parts[5] else 0
                    volume = float(parts[8]) if parts[8] else 0  # 成交量(手)
                    amount = float(parts[9]) if parts[9] else 0  # 成交额(万)

                    results[code] = StockQuote(
                        code=code, name=name, price=price, prev_close=prev_close,
                        open=open_, high=high, low=low,
                        volume=volume, amount=amount,
                        change=round(price - prev_close, 2) if prev_close else 0,
                        change_pct=round((price - prev_close) / prev_close * 100, 2) if prev_close else 0,
                        time_=f"{parts[30]} {parts[31]}" if len(parts) > 31 else ""
                    )
        except Exception as e:
            L.error(f"行情获取失败: {e}")

        return results

    def fetch_watchlist(self):
        """获取自选池行情"""
        with self._lock:
            codes = list(self.watchlist.keys())
        data = self.fetch_quote(codes)
        with self._lock:
            self.market_data.update(data)
        return data

    def search_stock(self, keyword):
        """搜索股票"""
        keyword = keyword.strip().upper()
        results = {}
        # 搜自选池
        for code, name in self.watchlist.items():
            if keyword in code.upper() or keyword in name:
                results[code] = name
        return results

    # ── 交易信号 ──
    def analyze_with_ai(self, code, quote):
        """AI分析生成交易信号"""
        if not self.llm:
            return TradeSignal(code, quote.name, "hold", quote.price,
                               reason="AI引擎未就绪", confidence=0)

        try:
            prompt = f"""分析A股 {quote.name}({code}) 当前行情:
现价: {quote.price} | 昨收: {quote.prev_close}
涨跌: {quote.change} ({quote.change_pct}%)
今开: {quote.open} | 最高: {quote.high} | 最低: {quote.low}
成交额: {quote.amount}万

请以专业交易员视角,输出:
1. 技术判断(1句话): 当前是否处于关键位置?
2. 操作建议: buy(买入)/sell(卖出)/hold(观望)
3. 置信度: 0-100的数字
4. 策略依据: 基于什么逻辑(如:突破箱体/超跌反弹/趋势跟踪等)

格式:
判断: xxx
操作: buy/sell/hold
置信度: 数字
策略: xxx"""

            resp = self.llm.invoke([{"role":"user","content":prompt}])

            action = "hold"
            reason = ""
            confidence = 0
            strategy = ""

            for line in resp.split("\n"):
                line = line.strip()
                if "操作" in line or "建议" in line:
                    if "buy" in line.lower() or "买入" in line:
                        action = "buy"
                    elif "sell" in line.lower() or "卖出" in line:
                        action = "sell"
                if "判断" in line or "分析" in line:
                    reason = line.split(":",1)[-1].strip()[:100]
                if "置信" in line:
                    nums = re.findall(r'(\d+)', line)
                    if nums:
                        confidence = min(int(nums[0]), 100)
                if "策略" in line:
                    strategy = line.split(":",1)[-1].strip()[:50]

            signal = TradeSignal(code, quote.name, action, quote.price,
                                 reason=reason or resp[:100],
                                 confidence=confidence,
                                 strategy=strategy)
            with self._lock:
                self.signals.appendleft(signal)

            if action != "hold":
                L.info(f"📊 交易信号: {quote.name} → {action.upper()} (置信度:{confidence}%) 策略:{strategy}")

            return signal

        except Exception as e:
            return TradeSignal(code, quote.name, "hold", quote.price,
                               reason=f"AI分析异常: {e}", confidence=0)

    def scan_market(self):
        """全市场扫描，生成交易信号"""
        data = self.fetch_watchlist()
        signals = []
        # 只扫描个股（非指数）
        for code, quote in data.items():
            if code.startswith("sh000") or code.startswith("sz399"):
                continue
            sig = self.analyze_with_ai(code, quote)
            signals.append(sig)
        
        # 按置信度排序
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    # ── 交易执行 ──
    def execute_trade(self, code, action, shares=100, price=None):
        """执行交易 (通过浏览器自动化或桌面应用)"""
        quote = self.market_data.get(code)
        name = quote.name if quote else code

        if not self.auto_trade:
            return {"ok": False, "msg": "⚠️ 自主交易已关闭。请在设置中开启 auto_trade。"}

        trade_price = price or (quote.price if quote else 0)

        log_entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "code": code, "name": name, "action": action,
            "shares": shares, "price": trade_price,
            "amount": round(shares * trade_price, 2),
            "status": "pending"
        }

        # 尝试通过浏览器打开交易平台
        platform_url = self.TRADING_PLATFORMS.get("东方财富交易", "https://jywg.eastmoney.com/")
        
        try:
            # 用系统默认浏览器打开交易页面
            os.startfile(platform_url)
            log_entry["status"] = "opened"
            log_entry["msg"] = f"已打开交易平台: {platform_url}"
        except Exception as e:
            log_entry["status"] = "error"
            log_entry["msg"] = f"无法打开交易平台: {e}"

        with self._lock:
            self.trade_log.appendleft(log_entry)

        return {"ok": True, "log": log_entry}

    # ── 仓位管理 ──
    def add_position(self, code, name, shares, cost):
        """添加持仓"""
        with self._lock:
            self.positions[code] = Position(code, name, shares, cost)

    def remove_position(self, code):
        """移除持仓"""
        with self._lock:
            if code in self.positions:
                del self.positions[code]

    def get_portfolio_value(self):
        """计算持仓市值"""
        if not self.positions:
            return 0, 0
        codes = list(self.positions.keys())
        quotes = self.fetch_quote(codes)
        total_cost = 0
        total_market = 0
        for code, pos in self.positions.items():
            total_cost += pos.shares * pos.avg_cost
            if code in quotes:
                total_market += pos.shares * quotes[code].price
        return total_cost, total_market

    # ── 浏览器操控 ──
    def open_platform(self, platform_name):
        """打开交易平台"""
        url = self.TRADING_PLATFORMS.get(platform_name)
        if url:
            try:
                os.startfile(url)
                return {"ok": True, "platform": platform_name, "url": url}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"未知平台: {platform_name}"}

    def get_status(self):
        """获取操盘状态"""
        with self._lock:
            cost, market = self.get_portfolio_value()
            return {
                "auto_trade": self.auto_trade,
                "watchlist_count": len(self.watchlist),
                "positions": {
                    code: {"name": p.name, "shares": p.shares, "avg_cost": p.avg_cost}
                    for code, p in self.positions.items()
                },
                "portfolio_cost": round(cost, 2),
                "portfolio_market": round(market, 2),
                "pnl": round(market - cost, 2) if cost > 0 else 0,
                "recent_signals": [
                    {"code": s.code, "name": s.name, "action": s.action,
                     "price": s.price, "confidence": s.confidence,
                     "reason": s.reason[:80], "strategy": s.strategy,
                     "time": s.time}
                    for s in list(self.signals)[:20]
                ],
                "trade_log": list(self.trade_log)[:20],
                "platforms": list(self.TRADING_PLATFORMS.keys())
            }
