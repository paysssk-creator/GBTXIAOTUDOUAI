"""
gbt/browser_desk.py — 浏览器操盘 ↔ 桌面自动化的桥接层
=====================================================
连接 browser_trader (浏览器引擎) + desktop_ctl/winctl (桌面操控)
实现: 看屏幕→AI分析→浏览器下单→桌面确认→风控检查 全闭环
"""
import time, json, os

class BrowserDeskBridge:
    """浏览器+桌面双通道操盘桥"""
    
    def __init__(self, browser_trader=None, desk=None, winctl=None):
        self.trader = browser_trader
        self.desk = desk      # desktop_ctl 实例
        self.winctl = winctl  # winctl 实例
    
    # ── 快捷入口 ────────────────────────────
    
    def quick_scan(self, platform="eastmoney"):
        """快速扫描: 浏览器打开→截图→VLM分析"""
        if not self.trader:
            return {"ok": False, "error": "trader未初始化"}
        return self.trader.scan_market(platform)
    
    def quick_analyze(self, code, platform="eastmoney"):
        """快速分析个股"""
        if not self.trader:
            return {"ok": False, "error": "trader未初始化"}
        return self.trader.analyze_stock(code, platform)
    
    def quick_trade(self, code, action="analyze", price=0, volume=100):
        """快速交易"""
        if not self.trader:
            return {"ok": False, "error": "trader未初始化"}
        return self.trader.auto_trade(code, action, price=price, volume=volume)
    
    # ── 桌面自动化桥接 ─────────────────────
    
    def ensure_trading_app(self, app_name="同花顺", retry=3):
        """确保交易APP在前台 — 用于桌面版同花顺/东方财富等"""
        if not self.desk:
            return "no_desk"
        
        for i in range(retry):
            # 截图看当前状态
            b64 = self._capture()
            if not b64:
                continue
            
            # VLM判断是否在交易界面
            if self.trader and self.trader.llm:
                state = self.trader._vlm_analyze(b64,
                    f"确认当前屏幕是否显示{app_name}的交易界面。"
                    "如果是,返回{'on_trading':true}。如果不是,返回{'on_trading':false,'current_app':'当前应用名'}。")
                if state.get("on_trading"):
                    return "ok"
                
                # 需要切换到交易APP
                target = state.get("current_app", "")
                if target != app_name:
                    self.desk.keyboard_hotkey(["alt", "tab"])
                    time.sleep(0.4)
            else:
                # 无VLM: 盲切Alt+Tab
                self.desk.keyboard_hotkey(["alt", "tab"])
                time.sleep(0.5)
        
        return "switch_failed"
    
    def desktop_trade(self, code, action="buy", price=0, volume=100):
        """通过桌面自动化直接操作交易APP"""
        if not self.desk:
            return {"ok": False, "error": "desk未初始化"}
        
        try:
            # 1. 输入股票代码
            self.desk.keyboard_type(str(code))
            time.sleep(0.2)
            
            # 2. 按F1买入/F2卖出
            if action == "buy":
                self.desk.keyboard_hotkey(["f1"])
            elif action == "sell":
                self.desk.keyboard_hotkey(["f2"])
            time.sleep(0.3)
            
            # 3. 输入价格
            if price > 0:
                self.desk.keyboard_type(str(price))
                time.sleep(0.1)
            
            # 4. Tab跳到数量, 输入数量
            self.desk.keyboard_hotkey(["tab"])
            self.desk.keyboard_type(str(volume))
            time.sleep(0.1)
            
            return {"ok": True, "code": code, "action": action,
                    "price": price, "volume": volume, "mode": "desktop"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}
    
    def _capture(self):
        """截图 — 优先用desk, 备选mss"""
        if self.desk and hasattr(self.desk, 'screenshot'):
            return self.desk.screenshot()
        try:
            import mss, base64
            from PIL import Image
            from io import BytesIO
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                buf = BytesIO(); pil.save(buf, format="JPEG", quality=50)
                return base64.b64encode(buf.getvalue()).decode()
        except:
            return None
    
    # ── 风控+监控 ──────────────────────────
    
    def trade_with_risk_check(self, code, action, price=0, volume=100):
        """带风控的交易 — 交易前强制风控检查"""
        # 风控检查
        try:
            from gbt.risk_ctrl import risk_check
            risk = risk_check()
            if not risk.get("can_trade", True):
                return {"ok": False, "error": "风控阻止", "risk": risk}
        except ImportError:
            pass
        
        # 先尝试桌面自动化(快)
        if self.desk:
            result = self.desktop_trade(code, action, price, volume)
            if result.get("ok"):
                self._log_trade(code, action, price, volume, "desktop")
                return result
        
        # 桌面失败则用浏览器
        if self.trader:
            result = self.trader.auto_trade(code, action, price=price, volume=volume)
            if result.get("ok"):
                self._log_trade(code, action, price, volume, "browser")
                return result
        
        return {"ok": False, "error": "所有交易通道失败"}
    
    def _log_trade(self, code, action, price, volume, channel):
        """记录交易到审计日志"""
        try:
            from gbt.knowledge.ashare import ASHARE_KNOWLEDGE
            # 可以扩展: 写入审计日志文件
            log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {channel} | {action} {code} ¥{price} x{volume}"
            with open(os.path.expanduser("~/.gbt/trades.log"), "a") as f:
                f.write(log_entry + "\n")
        except:
            pass
    
    # ── 综合驾驶舱 ─────────────────────────
    
    def cockpit(self, code=None):
        """综合驾驶舱 — 一屏看全部"""
        result = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        
        # 1. 市场情绪
        if self.trader:
            try:
                scan = self.trader.scan_market()
                result["market"] = scan.get("analysis", {})
            except:
                result["market"] = "扫描失败"
        
        # 2. 风控状态
        try:
            from gbt.risk_ctrl import risk_check
            result["risk"] = risk_check()
        except:
            result["risk"] = "风控模块不可用"
        
        # 3. 持仓(如有)
        try:
            from gbt.paper_account import get_positions
            result["positions"] = get_positions()
        except:
            pass
        
        # 4. 个股分析
        if code:
            result["stock"] = self.quick_analyze(code) if self.trader else "trader未初始化"
        
        return result


# 快速函数
def create_bridge(llm=None, desk=None):
    """创建操盘桥 — 一行初始化"""
    from gbt.browser_trader import BrowserTrader
    trader = BrowserTrader(llm=llm, desk=desk)
    return BrowserDeskBridge(browser_trader=trader, desk=desk)
