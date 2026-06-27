"""
ai_trader.py — AI操盘手 (Cradle GCC + A股交易)
截图交易软件→VLM分析K线/盘口→决策→自动下单→自省成交
"""
import json, time, base64, os
from io import BytesIO
from typing import Optional, Dict, List
from dataclasses import dataclass, field

try:
    from PIL import Image; HAS_PIL = True
except Exception: HAS_PIL = False
try:
    import mss; HAS_MSS = True
except Exception: HAS_MSS = False
try:
    from gbt.a_share_rules import a_share; HAS_A_SHARE = True
except Exception: HAS_A_SHARE = False

@dataclass
class TradeDecision:
    action: str = ""
    code: str = ""
    price: float = 0
    volume: int = 0
    reasoning: str = ""
    confidence: float = 0.0
    stop_loss: float = 0
    take_profit: float = 0

class AITrader:
    """AI操盘手: 截图→分析→决策→执行→自省"""
    def __init__(self, llm=None, desk=None):
        self.llm = llm; self.desk = desk
        self.history = []; self._visual = HAS_PIL and HAS_MSS

    def capture(self):
        if not self._visual: return None
        try:
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                pil = Image.frombytes("RGB",img.size,img.bgra,"raw","BGRX")
                buf = BytesIO(); pil.save(buf,format="JPEG",quality=50)
                return base64.b64encode(buf.getvalue()).decode()
        except Exception: return None

    def _call(self, msgs):
        if not self.llm: return "[No LLM]"
        try: return self.llm.invoke(msgs)
        except Exception as e: return f"[Error] {e}"

    def analyze_screen(self, b64, focus=""):
        """VLM分析交易软件截图"""
        msgs = [{"role":"system","content":'''你是A股职业操盘手。分析交易截图返回JSON:
{"app":"软件名","view":"K线/分时/盘口/持仓/下单","code":"股票代码",
"price":当前价,"trend":"上涨/下跌/震荡","volume_ratio":量比,
"buy_sell_ratio":"买卖盘比","support":支撑位,"resistance":压力位,
"indicators":"MACD/KDJ/RSI信号","sentiment":"市场情绪",
"risk_level":"低/中/高","suggestion":"操作建议"}'''}]
        content = [{"type":"text","text":f"分析交易截图{focus}:"}]
        if b64: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}})
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {"raw":raw}
        except Exception: return {"raw":raw}

    def decide(self, analysis, account_info=""):
        """做出交易决策"""
        msgs = [{"role":"system","content":'''你是A股量化交易决策AI。基于屏幕分析和账户信息做决策。
返回JSON:
{"action":"buy/sell/hold/watch","code":"股票代码",
"price":建议价格,"volume":建议数量(股),
"reasoning":"决策理由","confidence":0.0-1.0,
"stop_loss":止损价,"take_profit":止盈价}'''}]
        content = [{"type":"text","text":f"分析:{json.dumps(analysis,ensure_ascii=False)}\n账户:{account_info}\n交易决策:"}]
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            d = json.loads(raw[s:e]) if s>=0 and e>s else {}
            return TradeDecision(
                action=d.get("action","hold"),code=d.get("code",""),
                price=float(d.get("price",0)),volume=int(d.get("volume",0)),
                reasoning=d.get("reasoning",""),confidence=float(d.get("confidence",0)),
                stop_loss=float(d.get("stop_loss",0)),take_profit=float(d.get("take_profit",0)))
        except Exception: return TradeDecision(action="hold",reasoning="解析失败")
    def observe(self, b64, task=""):
        """先看再动: 截图分析当前状态, 确认是否已打开目标窗口"""
        msgs = [{"role":"system","content":'''你是电脑状态检查员。分析截图回答:
1. 当前前台窗口是什么应用?
2. 这是交易软件吗(东方财富/同花顺/券商)?
3. 如果任务已经完成, 返回 {"done":true,"reason":"..."}
4. 如果需要切窗口, 返回 {"need_switch":true,"target":"应用名"}

只返回JSON: {"app":"当前应用","is_trading":true/false,"done":false,"need_switch":false}'''}]
        content = [{"type":"text","text":f"检查当前状态: {task}"}]
        if b64: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}})
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {"app":"未知","is_trading":False,"done":False}
        except Exception: return {"app":"未知","is_trading":False,"done":False}

    def _ensure_trading_window(self, b64):
        """确保交易软件窗口在前台, 不盲目Alt+Tab"""
        state = self.observe(b64, "确认交易软件在前台")
        if state.get("done"):
            return "already_done"
        if state.get("is_trading"):
            return "ok"  # 已经在交易软件, 不切窗
        if state.get("need_switch"):
            # 精确切到目标窗口, 最多2次
            for _ in range(2):
                self.desk.keyboard_hotkey(["alt","tab"])
                time.sleep(0.4)
                b64 = self.capture()
                check = self.observe(b64, "确认已切换到交易软件")
                if check.get("is_trading"):
                    return "ok"
            return "switch_failed"
        return "ok"  # 看不出就继续, 不重复切

    def execute_trade(self, decision, b64_before=None):
        """执行交易: 先看再动, 不盲切窗口"""
        if not self.desk or decision.action == "hold":
            return {"ok":True,"action":"hold"}

        # 去重: 不重复执行相同操作
        key = f"{decision.action}:{decision.code}:{decision.price}"
        if hasattr(self, '_last_trade_key') and self._last_trade_key == key:
            return {"ok":True,"action":"hold","reason":"去重: 已执行过相同操作"}
        self._last_trade_key = key

        # A股规则: 数量必须为100股整数倍
        if HAS_A_SHARE:
            decision.volume = a_share.normalize_lot(decision.volume)
        if decision.volume < 100:
            return {"ok":False,"error":"A股交易数量不足1手(100股)"}

        try:
            # 1. 先确认交易窗口状态
            if b64_before:
                state = self.observe(b64_before, "确认交易窗口")
                if state.get("done"):
                    return {"ok":True,"action":"hold","reason":"任务已完成"}

            # 2. 只在需要时切换窗口
            if b64_before:
                window_ok = self._ensure_trading_window(b64_before)
                if window_ok == "already_done":
                    return {"ok":True,"action":"done","reason":"任务已完成, 不重复操作"}
                elif window_ok == "switch_failed":
                    pass  # 继续尝试, 不放弃

            # 3. 输入股票代码
            self.desk.keyboard_type(str(decision.code))
            time.sleep(0.2)

            # 4. 按买入/卖出快捷键
            if decision.action == "buy":
                self.desk.keyboard_hotkey(["f1"])
            elif decision.action == "sell":
                self.desk.keyboard_hotkey(["f2"])
            time.sleep(0.3)

            # 5. 输入价格
            self.desk.keyboard_type(str(decision.price))
            time.sleep(0.1)

            # 6. Tab跳到数量, 输入数量
            self.desk.keyboard_hotkey(["tab"])
            self.desk.keyboard_type(str(decision.volume))
            time.sleep(0.1)

            return {"ok":True,"action":decision.action,"code":decision.code,
                    "price":decision.price,"volume":decision.volume}
        except Exception as e:
            return {"ok":False,"error":str(e)}

    def reflect(self, b64b, b64a, decision):
        """自省: 订单成交了吗?"""
        msgs = [{"role":"system","content":'对比交易前后截图判断订单是否成交。返回JSON: {"filled":true/false,"reason":"..."}'}]
        content = [{"type":"text","text":f"决策:{decision.action} {decision.code} ¥{decision.price} x{decision.volume}\n成交了吗?"}]
        if b64b: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64b}"}})
        if b64a: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64a}"}})
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {"filled":False,"reason":raw[:100]}
        except Exception: return {"filled":False,"reason":raw[:100]}

    def run(self, task, focus="", account_info="", max_attempts=3):
        """完整AI操盘流程"""
        results = []
        for i in range(max_attempts):
            b64b = self.capture()
            if not b64b:
                results.append({"step":i+1,"error":"截图失败"}); continue
            analysis = self.analyze_screen(b64b, focus)
            decision = self.decide(analysis, account_info)
            if decision.action in ("hold","watch"):
                results.append({"step":i+1,"action":"hold","reasoning":decision.reasoning}); break
            exec_result = self.execute_trade(decision, b64b)
            time.sleep(1)
            b64a = self.capture()
            reflection = self.reflect(b64b, b64a, decision)
            filled = reflection.get("filled", False)
            results.append({"step":i+1,"decision":decision.action,"code":decision.code,
                "price":decision.price,"volume":decision.volume,"filled":filled,
                "confidence":decision.confidence,"reasoning":decision.reasoning})
            if filled: break
            time.sleep(2)
        return {"ok":any(r.get("filled") for r in results if "filled" in r),
                "task":task,"attempts":len(results),"results":results,
                "summary":"; ".join(f"S{r['step']}:{r.get('decision',r.get('action','?'))}"
                for r in results)}


def ai_trade(task, llm=None, desk=None, focus="", account=""):
    """快捷AI操盘"""
    return AITrader(llm=llm, desk=desk).run(task, focus=focus, account_info=account)
