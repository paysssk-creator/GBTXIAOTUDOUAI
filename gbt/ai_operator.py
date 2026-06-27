"""
ai_operator.py — GBT AI 设备操控总入口 v1.0
整合 DesktopController + ScreenOCR + Autopilot + AITrader，
实现 AI 自主观察屏幕、决策、操控电脑、执行交易。

所有能力按原项目设计完整保留，不做任何限制。
"""
import os, sys, time, json, base64, io, logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gbt import config as gbt_config

L = logging.getLogger("GBT.AIOperator")


@dataclass
class DeviceAction:
    """统一设备动作描述"""
    action_type: str
    params: Dict[str, Any]
    reasoning: str = ""


class AIDeviceOperator:
    """AI 设备操控器"""

    def __init__(self, llm_provider=None, safe_mode: bool = False):
        self.llm = llm_provider
        self.safe_mode = safe_mode
        self._init_modules()

    def _init_modules(self):
        from gbt.desktop_ctl import DesktopController
        from gbt.screen_ai import ScreenOCR, Voice
        from gbt.vision import VisionService
        from gbt.autopilot import Autopilot
        from gbt.gcc.ai_trader import AITrader

        self.desktop = DesktopController()
        self.screen = ScreenOCR()
        self.vision = VisionService()
        self.voice = Voice()
        self.autopilot = Autopilot(llm_provider=self.llm)
        self.ai_trader = AITrader(llm=self.llm, desk=self.desktop)
        L.info("AIDeviceOperator ready")


    def observe(self, region: tuple = None, save_path: str = None, use_llm: bool = False) -> Dict:
        """Observe screen: screenshot + OCR + optional vision LLM."""
        img = self.vision.screenshot(region=region, save_path=save_path)
        if img is None:
            return {"ok": False, "error": "screenshot failed"}
        ocr = self.screen.read_text(image=img)
        result = {"ok": True, "image_size": img.size, "timestamp": time.time(), "ocr": ocr}
        if use_llm:
            p = "Detailed screen description in Chinese."
            llm = self.vision.describe(img, prompt=p)
            result["llm"] = llm
            result["description"] = llm.get("description", "") if llm.get("ok") else ocr.get("text", "")
        else:
            result["description"] = ocr.get("text", "")
        return result

    def find_text(self, text: str, region: tuple = None) -> List[Dict]:
        return self.screen.find_text_on_screen(text, region=region)

    def act(self, action: DeviceAction) -> Dict:
        """执行一个设备动作"""
        if self.safe_mode:
            return {"ok": True, "simulated": True, "action": action.action_type, "params": action.params}

        t = action.action_type
        p = action.params
        desk = self.desktop

        try:
            if t == "click":
                return desk.click(p.get("x"), p.get("y"), p.get("button", "left"))
            elif t == "double_click":
                return desk.double_click(p.get("x"), p.get("y"))
            elif t == "move_to":
                return desk.move_to(p.get("x"), p.get("y"))
            elif t == "type":
                return desk.type_text(p.get("text", ""), p.get("interval", 0.05))
            elif t == "hotkey":
                return desk.hotkey(*p.get("keys", []))
            elif t == "press":
                return desk.press_key(p.get("key", "enter"))
            elif t == "paste":
                return desk.paste_text(p.get("text", ""))
            elif t == "focus_window":
                return desk.focus_window(p.get("title", ""))
            elif t == "maximize":
                return desk.maximize_window()
            elif t == "browser_navigate":
                return desk.browser_navigate(p.get("url", ""))
            elif t == "browser_find":
                return desk.browser_find_and_type(p.get("text", ""))
            elif t == "trade_flow":
                return desk.trade_platform_flow(
                    p.get("platform", "eastmoney"),
                    p.get("code", ""),
                    p.get("action", "buy"),
                    p.get("shares", 100),
                    p.get("price", 0)
                )
            elif t == "screenshot":
                return self.observe(region=p.get("region"), save_path=p.get("save_path"))
            elif t == "ocr":
                return self.screen.read_text(region=p.get("region"))
            elif t == "voice_speak":
                return self.voice.speak(p.get("text", ""))
            elif t == "launch_app":
                # Launch via Windows Run dialog: Win+R, type app name, press Enter
                desk.hotkey("win", "r")
                time.sleep(0.5)
                desk.type_text(p.get("app_name", ""), interval=0.01)
                time.sleep(0.3)
                desk.press_key("enter")
                return {"ok": True, "action": "launch_app", "app": p.get("app_name", "")}
            elif t == "wait":
                time.sleep(p.get("seconds", 1.0))
                return {"ok": True, "action": "wait"}
            else:
                return {"ok": False, "error": f"未知动作类型: {t}"}
        except Exception as e:
            L.error(f"执行动作失败 {t}: {e}")

    def decide(self, task: str, observation: Dict) -> List[DeviceAction]:
        """根据屏幕观察结果，让 LLM 生成下一步动作"""
        if self.llm is None:
            return self._fallback_decide(task, observation)

        ocr_text = observation.get("ocr", {}).get("text", "")[:1500]
        prompt = f"""你是 GBT AI 电脑操控助手。当前任务：{task}

屏幕 OCR 识别到的文字：
{ocr_text}

请根据当前屏幕状态，决定下一步操作。返回严格 JSON：
{{"observation":"判断","done":false,"actions":[
  {{"action_type":"click","params":{{"x":100,"y":200}},"reasoning":"点击"}},
  {{"action_type":"type","params":{{"text":"600519"}},"reasoning":"输入"}}
]}}

可用：click,double_click,move_to,type,hotkey,press,paste,focus_window,maximize,browser_navigate,screenshot,ocr,voice_speak,wait
任务完成则 done:true, actions为空。"""

        try:
            from gbt.autopilot import sanitize_json
            raw = self.llm.invoke([{"role": "user", "content": prompt}])
            plan = sanitize_json(raw)
            actions = []
            for a in plan.get("actions", []):
                actions.append(DeviceAction(
                    action_type=a.get("action_type", "wait"),
                    params=a.get("params", {}),
                    reasoning=a.get("reasoning", "")
                ))
            return actions
        except Exception as e:
            L.error(f"LLM 决策失败: {e}")
            return self._fallback_decide(task, observation)

    def _fallback_decide(self, task: str, observation: Dict) -> List[DeviceAction]:
        actions = []
        if "登录" in task or "login" in task.lower():
            actions.append(DeviceAction("ocr", {}, "检测登录状态"))
        elif "搜索" in task or "600519" in task:
            actions.extend([
                DeviceAction("hotkey", {"keys": ["ctrl", "f"]}, "打开搜索框"),
                DeviceAction("type", {"text": "600519"}, "输入股票代码"),
                DeviceAction("press", {"key": "enter"}, "确认搜索"),
            ])
        elif "买入" in task or "buy" in task.lower():
            actions.extend([
                DeviceAction("click", {"x": 700, "y": 500}, "点击买入"),
                DeviceAction("type", {"text": "100"}, "输入数量"),
                DeviceAction("press", {"key": "enter"}, "确认"),
            ])
        else:
            actions.append(DeviceAction("screenshot", {}, "截图观察"))
        return actions

    def run_task(self, task: str, max_steps: int = 10) -> Dict:
        """执行一个完整的自主电脑操控任务"""
        L.info(f"开始自主任务: {task}")
        steps = []
        for i in range(max_steps):
            obs = self.observe()
            if not obs["ok"]:
                return {"ok": False, "error": obs.get("error"), "steps": steps}
            actions = self.decide(task, obs)
            if not actions:
                return {"ok": True, "message": "任务完成", "steps": steps}
            for a in actions:
                result = self.act(a)
                steps.append({
                    "step": i + 1,
                    "action": a.action_type,
                    "params": a.params,
                    "reasoning": a.reasoning,
                    "result": result
                })
                if not result.get("ok"):
                    L.warning(f"动作失败: {a.action_type} - {result.get('error')}")
        return {"ok": True, "message": f"达到最大步数 {max_steps}", "steps": steps}

    def trade_autonomous(self, code: str, action: str = "buy", shares: int = 100) -> Dict:
        """AI 自主交易：截图分析 → 决策 → 操控交易软件"""
        b64 = self.ai_trader.capture()
        if not b64:
            return {"ok": False, "error": "无法截图"}
        analysis = self.ai_trader.analyze_screen(b64, focus=code)
        decision = self.ai_trader.decide(analysis, account_info="")

        if not self.safe_mode and decision.confidence > 0.6:
            result = self.desktop.trade_platform_flow(
                platform="eastmoney",
                code=code,
                action=action,
                shares=shares,
                price=decision.price
            )
        else:
            result = {"ok": True, "simulated": True, "decision": decision.__dict__}

        return {
            "ok": True,
            "analysis": analysis,
            "decision": decision.__dict__,
            "execution": result
        }


# 全局实例
ai_operator = AIDeviceOperator(safe_mode=not gbt_config.AUTO_AUTHORIZE)


def get_ai_operator():
    return ai_operator


def reload_ai_operator():
    """根据当前 AUTO_AUTHORIZE 配置重新创建全局 AI 操作器。"""
    global ai_operator
    ai_operator = AIDeviceOperator(safe_mode=not gbt_config.AUTO_AUTHORIZE)
    L.warning(f"AI 操作器已重新加载，自动授权={gbt_config.AUTO_AUTHORIZE}")
    return ai_operator
