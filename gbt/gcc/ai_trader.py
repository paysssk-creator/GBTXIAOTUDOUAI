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
except: HAS_PIL = False
try:
    import mss; HAS_MSS = True
except: HAS_MSS = False

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
        except: return None

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
        except: return {"raw":raw}

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
        except: return TradeDecision(action="hold",reasoning="解析失败")
    def execute_trade(self, decision):
        """执行交易: 快捷键操作交易软件"""
        if not self.desk or decision.action == "hold":
            return {"ok":True,"action":"hold"}
        try:
            self.desk.keyboard_hotkey(["alt","tab"])
            time.sleep(0.3)
            self.desk.keyboard_type(str(decision.code))
            time.sleep(0.2)
            if decision.action == "buy":
                self.desk.keyboard_hotkey(["f1"])
            elif decision.action == "sell":
                self.desk.keyboard_hotkey(["f2"])
            time.sleep(0.3)
            self.desk.keyboard_type(str(decision.price))
            time.sleep(0.1)
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
            exec_result = self.execute_trade(decision)
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