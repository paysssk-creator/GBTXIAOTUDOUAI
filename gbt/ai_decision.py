"""
ai_decision.py — AI决策引擎
整合: VLM截图分析 + LLM推理 + 技术指标 → 交易决策
"""
import time, json, logging, os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

L = logging.getLogger("gbt.decision")

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "decision_log.jsonl")


@dataclass
class TradeSignal:
    code: str
    name: str
    price: float = 0
    change_pct: float = 0
    signal: str = "HOLD"  # BUY / SELL / HOLD
    confidence: float = 0.0
    reasoning: str = ""
    stop_loss: float = 0
    take_profit: float = 0
    position_size: int = 0
    indicators: Dict = field(default_factory=dict)
    timestamp: str = ""


class AIDecisionEngine:
    """AI决策引擎 — 多因子融合"""
    def __init__(self, llm=None):
        self.llm = llm
        self.decisions = []
        self._load_history()

    def _load_history(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    for line in f.readlines()[-100:]:
                        self.decisions.append(json.loads(line.strip()))
        except Exception:
            pass

    def _log_decision(self, sig: TradeSignal):
        entry = {
            "code": sig.code, "name": sig.name, "price": sig.price,
            "signal": sig.signal, "confidence": sig.confidence,
            "reasoning": sig.reasoning[:200],
            "timestamp": datetime.now().isoformat(),
        }
        self.decisions.append(entry)
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def analyze(self, quote: Dict, klines: List[Dict] = None,
                positions: Dict = None, account: Dict = None,
                mode: str = "conservative") -> TradeSignal:
        """多因子分析 → 生成交易信号"""
        code = quote.get("code", "")
        name = quote.get("name", "")
        price = quote.get("price", 10)
        change_pct = quote.get("change_pct", 0)

        sig = TradeSignal(code=code, name=name, price=price,
                          change_pct=change_pct, timestamp=time.strftime("%H:%M:%S"))

        # ── 因子1: 技术指标 ──
        score_tech = 0  # -100 to +100
        indicators = {}

        if klines and len(klines) >= 20:
            closes = [k["close"] for k in klines]
            # MA
            ma5 = sum(closes[-5:]) / 5
            ma10 = sum(closes[-10:]) / 10
            ma20 = sum(closes[-20:]) / 20
            indicators["ma5"] = round(ma5, 2)
            indicators["ma10"] = round(ma10, 2)
            indicators["ma20"] = round(ma20, 2)
            if price > ma5 > ma10:
                score_tech += 20
            elif price < ma5 < ma10:
                score_tech -= 20

            # RSI (14)
            gains = [max(0, closes[i] - closes[i - 1]) for i in range(1, min(15, len(closes)))]
            losses = [max(0, closes[i - 1] - closes[i]) for i in range(1, min(15, len(closes)))]
            avg_gain = sum(gains) / max(len(gains), 1)
            avg_loss = sum(losses) / max(len(losses), 1)
            rsi = 50 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
            indicators["rsi"] = round(rsi, 1)
            if rsi < 30:
                score_tech += 15
                sig.reasoning += f"RSI超卖({rsi:.0f}); "
            elif rsi > 70:
                score_tech -= 15
                sig.reasoning += f"RSI超买({rsi:.0f}); "

            # MACD
            ema12 = closes[-1]
            ema26 = closes[-1]
            for c in closes[-26:]:
                ema12 = ema12 * (11 / 13) + c * (2 / 13)
                ema26 = ema26 * (25 / 27) + c * (2 / 27)
            dif = ema12 - ema26
            indicators["macd_dif"] = round(dif, 3)
            if dif > 0:
                score_tech += 10

            # 布林带
            std = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5
            bb_upper = ma20 + 2 * std
            bb_lower = ma20 - 2 * std
            indicators["bb_upper"] = round(bb_upper, 2)
            indicators["bb_lower"] = round(bb_lower, 2)
            if price <= bb_lower:
                score_tech += 10
            elif price >= bb_upper:
                score_tech -= 10

            # 成交量
            avg_vol = sum(k.get("volume", 0) for k in klines[-10:]) / 10
            last_vol = klines[-1].get("volume", 0)
            if last_vol > avg_vol * 1.5 and change_pct > 0:
                score_tech += 10
                sig.reasoning += "放量上涨; "

            sig.indicators = indicators

        # ── 因子2: 价格动量 ──
        if change_pct > 1:
            score_tech += 10
        elif change_pct < -1:
            score_tech -= 10

        # ── 因子3: 持仓检查 ──
        if positions and code in positions:
            pos = positions[code]
            avg_cost = pos.get("avg_cost", price)
            pnl_pct = (price - avg_cost) / avg_cost * 100 if avg_cost else 0
            sig.position_shares = pos.get("shares", 0)
            sig.pnl_pct = round(pnl_pct, 2)
            # 止损
            if mode == "conservative" and pnl_pct <= -5:
                sig.signal = "SELL"
                sig.reasoning = f"触发保守止损 (盈亏{pnl_pct:.1f}% ≤ -5%)"
                sig.confidence = 0.95
                self._log_decision(sig)
                return sig
            elif pnl_pct <= -8:
                sig.signal = "SELL"
                sig.reasoning = f"触发强制止损 (盈亏{pnl_pct:.1f}% ≤ -8%)"
                sig.confidence = 0.99
                self._log_decision(sig)
                return sig
            # 止盈
            if pnl_pct >= 15:
                sig.signal = "SELL"
                sig.reasoning = f"触发止盈 (盈亏{pnl_pct:.1f}% ≥ 15%)"
                sig.confidence = 0.9
                self._log_decision(sig)
                return sig

        # ── 因子4: LLM增强（DeepSeek-reasoner 深度推理）──
        if self.llm and abs(change_pct) > 0.3:
            try:
                llm_prompt = f"""你是一名A股量化分析师。请基于以下数据对股票{code} {name}给出简洁判断:

现价: ¥{price} | 涨跌: {change_pct:+.2f}%
技术指标: MA5={indicators.get('ma5','N/A')} MA20={indicators.get('ma20','N/A')} RSI={indicators.get('rsi','N/A')} MACD_DIF={indicators.get('macd_dif','N/A')}

请只回复: BUY/SELL/HOLD + 1句话理由（≤20字）"""
                resp = self.llm._client.chat.completions.create(
                    model=self.llm.model,
                    messages=[{"role": "user", "content": llm_prompt}],
                    max_tokens=120, temperature=0.3)
                llm_out = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if "BUY" in llm_out.upper():
                    score_tech += 25
                    sig.reasoning += f"AI:BUY; "
                elif "SELL" in llm_out.upper():
                    score_tech -= 25
                    sig.reasoning += f"AI:SELL; "
            except Exception as e:
                L.debug(f"LLM decision skip: {e}")

        # ── 最终决策 ──
        sig.confidence = min(abs(score_tech) / 85, 0.95)

        if score_tech >= 30:
            sig.signal = "BUY"
            sig.reasoning += f"综合评分={score_tech} 偏多"
            sig.stop_loss = round(price * 0.95, 2)
            sig.take_profit = round(price * 1.10, 2)
        elif score_tech <= -30:
            sig.signal = "SELL"
            sig.reasoning += f"综合评分={score_tech} 偏空"
        else:
            sig.signal = "HOLD"
            sig.reasoning += f"评分={score_tech} 观望"

        # 仓位计算
        if sig.signal == "BUY" and account:
            cash = account.get("cash", 0)
            max_pct = 0.15 if mode == "conservative" else 0.30
            max_spend = cash * max_pct
            sig.position_size = max(100, int(max_spend / price / 100) * 100)
        elif sig.signal == "SELL" and positions:
            sig.position_size = positions.get(code, {}).get("shares", 0)

        self._log_decision(sig)
        return sig


# 全局单例
_engine = None


def get_engine(llm=None) -> AIDecisionEngine:
    global _engine
    if _engine is None:
        _engine = AIDecisionEngine(llm=llm)
    return _engine
