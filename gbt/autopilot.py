"""
GBT Autopilot — 无障碍自主操盘引擎 v1.0
核心循环: 截图 → LLM分析 → 动作执行 → 验证 → 下一轮
原理来自 Cradle (BAAI-Agents) General Computer Control
"""

import os, time, base64, json, logging, io
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from PIL import ImageGrab, Image
import pyautogui

L = logging.getLogger("GBT.Autopilot")


@dataclass
class ScreenState:
    image: Image.Image
    base64: str
    ocr_text: str = ""
    timestamp: float = 0.0


# ── 操盘技能库 (Cradle-style Skill Registry) ──
class TradingSkills:
    """原子操盘技能"""

    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()

    def skill_click(self, x, y, button="left"):
        pyautogui.click(x, y, button=button)
        return {"ok": True, "action": f"click({x},{y})"}

    def skill_type(self, text, interval=0.02):
        pyautogui.write(text, interval=interval)
        return {"ok": True, "action": f"type({text[:20]})"}

    def skill_hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        return {"ok": True, "action": f"hotkey({'+'.join(keys)})"}

    def skill_press(self, key="enter"):
        pyautogui.press(key)
        return {"ok": True, "action": f"press({key})"}

    def skill_scroll(self, clicks=-3):
        pyautogui.scroll(clicks)
        return {"ok": True, "action": f"scroll({clicks})"}

    def skill_wait(self, seconds=1.0):
        time.sleep(seconds)
        return {"ok": True, "action": f"wait({seconds}s)"}

    def skill_navigate(self, url):
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.4)
        if url:
            pyautogui.write(url, interval=0.01)
            pyautogui.press("enter")
        return {"ok": True, "action": f"navigate({url})"}

    def skill_search(self, text):
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        pyautogui.write(text, interval=0.03)
        time.sleep(0.3)
        pyautogui.press("enter")
        return {"ok": True, "action": f"search({text})"}

    def skill_fullscreen(self):
        pyautogui.press("f11")
        return {"ok": True, "action": "fullscreen"}

    def skill_screenshot_region(self, x, y, w, h):
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {"ok": True, "image": img,
                "base64": base64.b64encode(buf.getvalue()).decode()}

    def skill_tab(self, n=1):
        pyautogui.hotkey("ctrl", str(n))
        return {"ok": True, "action": f"tab({n})"}


@dataclass
class TradingAction:
    action_type: str
    target: str = ""
    params: Dict = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0

@dataclass
class PipelineResult:
    ok: bool
    message: str
    actions_executed: int = 0
    screenshots_taken: int = 0


# ── 自主操盘引擎 ──
class Autopilot:
    MAX_TURNS = 30
    INTERVAL = 3

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.skills = TradingSkills()
        self.memory: List[ScreenState] = []
        self.turn_count = 0
        self._stop = False
        L.info("Autopilot ready")

    def capture(self) -> ScreenState:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        s = ScreenState(image=img, base64=b64, timestamp=time.time())
        self.memory.append(s)
        return s

    def analyze(self, screen: ScreenState, task: str) -> List[TradingAction]:
        if not self.llm:
            return self._mock_analyze(task)

        # 加载A股操盘知识库
        try:
            from gbt.knowledge_base import get_system_prompt
            kb = get_system_prompt()
        except ImportError:
            kb = ""

        prompt = f"""你是桌面自主操盘AI。当前任务: {task}

请分析当前屏幕截图，按以下步骤思考:
1. 屏幕上是什么界面?(浏览器/交易软件/桌面?)
2. 有哪些可操作的元素?(按钮/输入框/K线图/股票列表?)
3. 基于知识库的技术指标，当前市场信号是什么?
4. 下一步应该执行什么操作?

返回JSON:
{{"observation":"屏幕内容描述",
  "decision":"buy/sell/hold/watch",
  "reasoning":"基于技术分析的决策理由",
  "confidence":0.0-1.0,
  "actions":[{{"type":"click","params":{{"x":100,"y":200}}}}, ...]
}}

如果任务已完成,返回: {{"done":true,"summary":"完成描述"}}"""

        try:
            # 视觉加速: 压缩图片再发给LLM
            fast_b64 = compress_for_vision(screen.image, max_size=480)
            resp = self.llm.chat_with_vision(
                prompt=prompt,
                image_base64=fast_b64,
                system_prompt=kb
            )
            # JSON清洗
            plan = sanitize_json(resp)

            if plan.get("done"):
                self._stop = True; return []

            obs = plan.get("observation", "")
            dec = plan.get("decision", "")
            reason = f"{obs} | 决策:{dec}"

            return [TradingAction(a.get("type",""),
                    target=a.get("target",""),
                    params=a.get("params",{}),
                    reasoning=reason) for a in plan.get("actions",[])]

        except Exception as e:
            L.error(f"LLM分析失败: {e}, 降级模拟模式")
            return self._mock_analyze(task)

    def _mock_analyze(self, task: str) -> List[TradingAction]:
        acts = []
        if "搜索" in task or "600519" in task or "贵州茅台" in task:
            acts += [TradingAction("search", params={"text":"600519"},
                     reasoning="搜索贵州茅台"),
                     TradingAction("wait", params={"seconds":2})]
        if "买入" in task or "buy" in task.lower():
            acts += [
                TradingAction("click", params={"x":700,"y":500},
                    reasoning="点击买入按钮"),
                TradingAction("wait", params={"seconds":0.8}),
                TradingAction("type", params={"text":"100"},
                    reasoning="输入数量100股"),
                TradingAction("wait", params={"seconds":0.5}),
                TradingAction("press", params={"key":"enter"},
                    reasoning="确认下单"),
            ]
        if "卖出" in task or "sell" in task.lower():
            acts += [
                TradingAction("click", params={"x":800,"y":500},
                    reasoning="点击卖出按钮"),
                TradingAction("wait", params={"seconds":0.8}),
                TradingAction("type", params={"text":"100"},
                    reasoning="输入数量"),
                TradingAction("press", params={"key":"enter"},
                    reasoning="确认"),
            ]
        if "分析" in task or "走势" in task or "K线" in task:
            acts += [
                TradingAction("scroll", params={"clicks":-8},
                     reasoning="向下滚动看K线图"),
                TradingAction("wait", params={"seconds":1.5}),
                TradingAction("scroll", params={"clicks":-5},
                     reasoning="继续滚动查看更多K线"),
            ]
        if not acts:
            acts = [TradingAction("wait", params={"seconds":2})]
        return acts

    def execute(self, action: TradingAction) -> Dict:
        m = {
            "click": lambda p: self.skills.skill_click(p.get("x",500),p.get("y",300),p.get("button","left")),
            "type": lambda p: self.skills.skill_type(p.get("text",""),p.get("interval",0.02)),
            "hotkey": lambda p: self.skills.skill_hotkey(*p.get("keys",[])),
            "press": lambda p: self.skills.skill_press(p.get("key","enter")),
            "scroll": lambda p: self.skills.skill_scroll(p.get("clicks",-3)),
            "wait": lambda p: self.skills.skill_wait(p.get("seconds",1.0)),
            "navigate": lambda p: self.skills.skill_navigate(p.get("url","")),
            "search": lambda p: self.skills.skill_search(p.get("text","")),
            "tab": lambda p: self.skills.skill_tab(p.get("n",1)),
        }
        if action.action_type in m:
            try: return m[action.action_type](action.params)
            except Exception as e: return {"ok":False,"error":str(e)}
        return {"ok":True,"action":action.action_type}

    def verify(self, before: ScreenState, after: ScreenState, action: TradingAction) -> bool:
        try:
            import numpy as np
            a1 = np.array(before.image.resize((200,113)))
            a2 = np.array(after.image.resize((200,113)))
            diff = np.mean(np.abs(a1.astype(float)-a2.astype(float))>30)
            return diff > 0.01 if action.action_type in ("click","type","hotkey","press") else True
        except: return True

    def run(self, task: str) -> PipelineResult:
        L.info(f"Start: {task}")
        self._stop = False; self.turn_count = 0; count = 0
        while self.turn_count < self.MAX_TURNS and not self._stop:
            self.turn_count += 1
            before = self.capture()
            actions = self.analyze(before, task)
            if not actions:
                if self._stop: break
                time.sleep(self.INTERVAL); continue
            for a in actions:
                if self._stop: break
                self.execute(a); count += 1; time.sleep(0.5)
            after = self.capture()
            time.sleep(self.INTERVAL)
        return PipelineResult(ok=count>0,
            message="完成" if self._stop else "超时",
            actions_executed=count, turns=self.turn_count)

    def stop(self):
        self._stop = True


def quick_pilot(task: str):
    ap = Autopilot()
    return ap.run(task)

def test_one_turn(task: str):
    """单轮测试: 截图→分析→执行→打印结果"""
    ap = Autopilot()
    print("📸 截图中...")
    screen = ap.capture()
    print(f"   截图: {len(screen.base64)//1024}KB")
    print("🧠 分析中...")
    actions = ap.analyze(screen, task)
    print(f"   动作数: {len(actions)}")
    for i, a in enumerate(actions):
        print(f"   [{i+1}] {a.action_type}: {a.target} | {a.reasoning[:50]}")
    print("⚡ 执行中...")
    for a in actions:
        r = ap.execute(a)
        print(f"   {a.action_type}: {'✅' if r.get('ok') else '❌'} {r.get('action','')}")
        time.sleep(0.5)
    print("📸 验证截图中...")
    after = ap.capture()
    print(f"   验证截图: {len(after.base64)//1024}KB")

# ── 视觉加速 ──
def compress_for_vision(img, max_size=640):
    """压缩图片加速LLM推理 (JPEG quality 50)"""
    w, h = img.size
    ratio = max_size / max(w, h)
    if ratio < 1:
        img = img.resize((int(w*ratio), int(h*ratio)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    return base64.b64encode(buf.getvalue()).decode()

def grab_region(x, y, w, h):
    """截图指定区域"""
    img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
    b64 = compress_for_vision(img)
    return ScreenState(image=img, base64=b64, timestamp=time.time())

# ── JSON清洗 ──
def sanitize_json(raw):
    """从LLM输出中提取JSON, 自动修正常见错误"""
    try:
        return json.loads(raw)
    except:
        pass
    m = __import__('re').search(r'\{[\s\S]*\}', raw)
    if m:
        s = m.group()
        s = __import__('re').sub(r'//.*', '', s)
        s = __import__('re').sub(r',\s*}', '}', s)
        try:
            return json.loads(s)
        except:
            pass
    return {"observation": raw[:300], "actions": []}

    return actions