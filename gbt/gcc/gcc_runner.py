"""
gcc_runner.py — General Computer Control Runner
借鉴 Cradle (BAAI-Agents/Cradle): 截图→分析→规划→执行→自省
"""
import os, time, json, base64, logging
try: import pyautogui; HAS_PYAUTOGUI = True
except ImportError: HAS_PYAUTOGUI = False
from io import BytesIO

L = logging.getLogger("GBT.GCC")
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from gbt.desktop_ctl import DesktopController
from gbt.llm import GBTLLM
from gbt.gcc.skill_curation import get_curator
try:
    from PIL import Image; HAS_PIL = True
except: HAS_PIL = False
try:
    import mss; HAS_MSS = True
except: HAS_MSS = False

@dataclass
class GCCAction:
    action: str = ""
    params: Dict = field(default_factory=dict)
    reasoning: str = ""

@dataclass
class GCCStep:
    step_id: int = 0
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    action: Optional[GCCAction] = None
    llm_analysis: str = ""
    llm_plan: str = ""
    self_reflection: str = ""
    success: Optional[bool] = None


class GCCRunner:
    MAX_STEPS = 20; MAX_EMPTY = 3

    def __init__(self, llm=None):
        self.llm = llm; self.desk = DesktopController()
        self.steps = []; self.running = False
        self._visual = HAS_PIL and HAS_MSS

    def capture(self):
        if not self._visual: return None
        try:
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                pil = Image.frombytes("RGB",img.size,img.bgra,"raw","BGRX")
                buf = BytesIO(); pil.save(buf,format="JPEG",quality=55)
                return base64.b64encode(buf.getvalue()).decode()
        except: return None

    def _call(self, msgs):
        if not self.llm: return "[No LLM]"
        try:
            return self.llm.invoke(msgs)
        except Exception as e:
            return f"[Error] {e}"
    def analyze(self, b64, task, hist=""):
        msgs = [{"role":"system","content":"分析屏幕: 当前界面/可交互元素/任务进度。简洁中文。"}]
        content = [{"type":"text","text":f"任务:{task}\n历史:{hist}\n分析屏幕:"}]
        self._img(content, b64)
        msgs.append({"role":"user","content":content})
        return self._call(msgs)
    def observe(self, b64, task=""):
        """Cradle-style 状态观察: 识别当前窗口、判断任务是否完成、是否需要切换"""
        msgs = [{"role":"system","content":'''你是窗口状态检测器。分析截图返回JSON:
{"app":"当前前台应用","is_target":true/false,"done":false,"need_switch":false,"target":"目标应用名","elements":["可见元素"]}'''}]
        content = [{"type":"text","text":f"任务:{task}"}]
        self._img(content, b64)
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {"app":"未知","is_target":False,"done":False}
        except Exception as e:
            L.debug(f"JSON解析失败: {e}")
            return {"app":"未知","is_target":False,"done":False}

    def plan(self, b64, task, analysis, hist=""):
        msgs = [{"role":"system","content":'输出JSON:{"action":"click/type/hotkey/move/scroll/wait/done","params":{...},"reasoning":"..."}'}]
        content = [{"type":"text","text":f"任务:{task}\n分析:{analysis}\n历史:{hist}\n输出操作JSON:"}]
        self._img(content, b64)
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {}
        except Exception as e:
            L.debug(f"计划JSON解析失败: {e}")
            return {"action":"wait","params":{"seconds":1},"reasoning":"解析失败"}

    def execute(self, action):
        try:
            a,p=action.get("action",""),action.get("params",{})
            if a=="click": self.desk.mouse_click(p.get("x",0),p.get("y",0),p.get("button","left"))
            elif a=="type": self.desk.keyboard_type(p.get("text",""))
            elif a=="hotkey" and p.get("keys"): self.desk.keyboard_hotkey(p["keys"])
            elif a=="move": self.desk.mouse_move(p.get("x",0),p.get("y",0))
            elif a=="scroll": self.desk.mouse_scroll(p.get("amount",0))
            elif a=="wait": time.sleep(min(p.get("seconds",1),10))
            return True
        except: return False

    def reflect(self, b64b, b64a, action, task):
        msgs = [{"role":"system","content":"判断操作是否成功。回复:成功/失败+原因。"}]
        content = [{"type":"text","text":f"任务:{task}\n操作:{json.dumps(action,ensure_ascii=False)}"}]
        self._img(content, b64b)
        if b64a: self._img(content, b64a)
        msgs.append({"role":"user","content":content})
        return self._call(msgs)
    def run(self, task, max_steps=None, verbose=True):
        if max_steps is None: max_steps = self.MAX_STEPS
        self.running = True; self.steps = []; empty = 0; hist = ""
        for i in range(max_steps):
            if not self.running: break
            step = GCCStep(step_id=i+1)
            shot = self.capture(); step.screenshot_before = shot
            step.llm_analysis = self.analyze(shot, task, hist)
            action = self.plan(shot, task, step.llm_analysis, hist)
            step.llm_plan = json.dumps(action, ensure_ascii=False)
            if action.get("action") == "done":
                step.success = True
                step.action = GCCAction("done",action.get("params",{}),action.get("reasoning",""))
                self.steps.append(step); break
            if action.get("action") in ("wait","",None):
                empty += 1
                if empty >= self.MAX_EMPTY:
                    step.success = True; self.steps.append(step); break
            else: empty = 0
            step.action = GCCAction(action.get("action",""),action.get("params",{}),action.get("reasoning",""))
            self.execute(action); time.sleep(0.3)
            shot2 = self.capture(); step.screenshot_after = shot2
            step.self_reflection = self.reflect(shot, shot2, action, task)
            step.success = "成功" in step.self_reflection
            self.steps.append(step)
            hist = "; ".join([f"S{s.step_id}:{s.action.action if s.action else'?'}→{'OK' if s.success else 'X'}" for s in self.steps[-3:]])
            if verbose:
                print(f"[Step {i+1}] {'✅' if step.success else '⚠️'} {action.get('action')} {step.self_reflection[:60]}")
        self.running = False
        ok = any(s.success for s in self.steps) if self.steps else False
        # ── Skill Curation: 成功后自动提取技能 ──
        try:
            curator = get_curator()
            skill = curator.extract_skill(self.steps, task, success=ok)
            if skill:
                curator.save_skill(skill)
                if verbose:
                    print(f"[Skill] 已提取技能: {skill.name}")
        except Exception as e:
            L.debug(f"技能提取失败: {e}")
        return {"ok":ok,"task":task,"total_steps":len(self.steps),
            "steps":[{"id":s.step_id,"action":s.action.action if s.action else"?",
            "success":s.success,"reflection":s.self_reflection[:150]} for s in self.steps]}

    def stop(self): self.running = False

    def _img(self, content, b64):
        if b64: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}})


def gcc_run(task, llm=None, max_steps=15):
    return GCCRunner(llm=llm).run(task, max_steps=max_steps)


# ═══════════════════════════════════════════════════════
# Game Mode — 实时游戏操控引擎
# ═══════════════════════════════════════════════════════

try:
    import ctypes, ctypes.wintypes
    _user32 = ctypes.windll.user32
    _gdi32 = ctypes.windll.gdi32
    HAS_DXGI = True
except Exception:
    HAS_DXGI = False


class GameController:
    """游戏级操控：连续输入 + 快速截图 + 像素检测"""

    def __init__(self):
        self.desk = DesktopController() if HAS_PYAUTOGUI else None
        self._pressed_keys = set()

    # ── 连续输入 ──
    def key_down(self, key):
        """持续按下（WASD移动）"""
        pyautogui.keyDown(key)
        self._pressed_keys.add(key)

    def key_up(self, key):
        pyautogui.keyUp(key)
        self._pressed_keys.discard(key)

    def key_tap(self, key, duration=0.05):
        pyautogui.press(key, presses=1, interval=duration)

    def release_all(self):
        for k in list(self._pressed_keys):
            self.key_up(k)

    def mouse_move_to(self, x, y, duration=0.01):
        pyautogui.moveTo(x, y, duration=duration)

    def mouse_down(self, button="left"):
        pyautogui.mouseDown(button=button)

    def mouse_up(self, button="left"):
        pyautogui.mouseUp(button=button)

    def mouse_click(self, x, y, button="left"):
        pyautogui.click(x, y, button=button)

    # ── 快速截图 (mss 内存抓取, <10ms) ──
    def fast_capture(self, region=None):
        """内存级截图，不编码JPEG，直接返回 numpy 数组"""
        if not HAS_MSS:
            return None
        with mss.mss() as sct:
            if region:
                monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
            else:
                monitor = sct.monitors[1]
            img = sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

    def fast_capture_region(self, x, y, w, h):
        """截取指定区域"""
        return self.fast_capture((x, y, w, h))

    # ── 像素检测（最快目标检测，<1ms） ──
    def pixel_at(self, pil_img, x, y):
        """获取指定像素颜色"""
        return pil_img.getpixel((x, y))

    def pixel_match(self, pil_img, x, y, target_rgb, tolerance=10):
        """单像素颜色匹配"""
        r, g, b = pil_img.getpixel((x, y))
        tr, tg, tb = target_rgb
        return abs(r - tr) <= tolerance and abs(g - tg) <= tolerance and abs(b - tb) <= tolerance

    def find_color_region(self, pil_img, target_rgb, tolerance=10, step=4):
        """扫描全图找目标颜色区域，返回 (x, y)"""
        w, h = pil_img.size
        for y in range(0, h, step):
            for x in range(0, w, step):
                if self.pixel_match(pil_img, x, y, target_rgb, tolerance):
                    return (x, y)
        return None

    def find_template(self, pil_img, template_path, confidence=0.8):
        """OpenCV 模板匹配 - 找图标/文字"""
        try:
            import cv2
            import numpy as np
            screen = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            template = cv2.imread(template_path)
            if template is None:
                return None
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= confidence:
                h, w = template.shape[:2]
                return (max_loc[0] + w // 2, max_loc[1] + h // 2)
            return None
        except ImportError:
            return None

    # ── 游戏状态机 ──
    def game_loop(self, state_fn, action_fn, fps=30, max_seconds=300):
        """游戏主循环：截图→状态检测→动作→循环"""
        import time as _time
        frame_time = 1.0 / fps
        start = _time.time()
        while _time.time() - start < max_seconds:
            frame_start = _time.time()
            img = self.fast_capture()
            state = state_fn(img) if img else "no_image"
            action_fn(state)
            elapsed = _time.time() - frame_start
            if elapsed < frame_time:
                _time.sleep(frame_time - elapsed)