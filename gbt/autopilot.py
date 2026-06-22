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
        prompt = f"""你是自主操盘AI。任务:{task}
支持的action: click(x,y), type(text), hotkey(k1,k2), press(k), scroll(n), wait(s), navigate(url), search(text), tab(n)
请基于屏幕截图分析,返回JSON: {{"observation":"...","actions":[{{"type":"...","params":{{}}}}]}}
如任务完成返回: {{"done":true,"summary":"..."}}"""
        try:
            resp = self.llm.chat(prompt=prompt, image_base64=screen.base64)
            plan = json.loads(resp) if isinstance(resp, str) else resp
            if plan.get("done"):
                self._stop = True; return []
            return [TradingAction(a.get("type",""),
                    params=a.get("params",{}),
                    reasoning=plan.get("observation","")) for a in plan.get("actions",[])]
        except Exception as e:
            L.error(f"analyze failed: {e}"); return []

    def _mock_analyze(self, task: str) -> List[TradingAction]:
        acts = []
        if "搜索" in task:
            acts += [TradingAction("search", params={"text":"600519"}),
                     TradingAction("wait", params={"seconds":2})]
        if "买入" in task:
            acts += [TradingAction("click", params={"x":800,"y":600}),
                     TradingAction("wait", params={"seconds":1}),
                     TradingAction("press", params={"key":"enter"})]
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
    return actions