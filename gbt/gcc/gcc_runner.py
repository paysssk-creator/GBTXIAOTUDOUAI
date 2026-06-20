"""
gcc_runner.py — General Computer Control Runner
借鉴 Cradle (BAAI-Agents/Cradle): 截图→分析→规划→执行→自省
"""
import os, time, json, base64
from io import BytesIO
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from gbt.desktop_ctl import DesktopController
from gbt.llm import GBTLLM
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
    def analyze(self, b64, task, hist=""):
        msgs = [{"role":"system","content":"分析屏幕: 当前界面/可交互元素/任务进度。简洁中文。"}]
        content = [{"type":"text","text":f"任务:{task}\n历史:{hist}\n分析屏幕:"}]
        self._img(content, b64)
        msgs.append({"role":"user","content":content})
        return self._call(msgs)

    def plan(self, b64, task, analysis, hist=""):
        msgs = [{"role":"system","content":'输出JSON:{"action":"click/type/hotkey/move/scroll/wait/done","params":{...},"reasoning":"..."}'}]
        content = [{"type":"text","text":f"任务:{task}\n分析:{analysis}\n历史:{hist}\n输出操作JSON:"}]
        self._img(content, b64)
        msgs.append({"role":"user","content":content})
        raw = self._call(msgs)
        try:
            s=raw.find("{"); e=raw.rfind("}")+1
            return json.loads(raw[s:e]) if s>=0 and e>s else {}
        except:
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
        return {"ok":ok,"task":task,"total_steps":len(self.steps),
            "steps":[{"id":s.step_id,"action":s.action.action if s.action else"?",
            "success":s.success,"reflection":s.self_reflection[:150]} for s in self.steps]}

    def stop(self): self.running = False


def gcc_run(task, llm=None, max_steps=15):
    return GCCRunner(llm=llm).run(task, max_steps=max_steps)
        self._img(content, b64b); self._img(content, b64a)
        msgs.append({"role":"user","content":content})
        return self._call(msgs)
        try: return self.llm.invoke(msgs)
        except Exception as e: return f"[Error] {e}"

    def _img(self, content, b64):
        if b64: content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}})
