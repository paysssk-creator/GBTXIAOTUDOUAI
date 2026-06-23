"""
gbt/skills/screenpipe_monitor.py - 24/7 屏幕/音频监控能力
可独立运行: python -m gbt.skills.screenpipe_monitor start
统一调度: 通过 SmartRouter 匹配"屏幕监控"/"开始录制"等关键词
"""
import sys
from .base import Skill, SkillResult, registry
from gbt.adapters.screenpipe import start, stop, status, recent


class ScreenpipeMonitorSkill(Skill):
    name = "screenpipe_monitor"
    category = "desktop"
    description = "24/7 持续屏幕/音频监控与回放"
    keywords = [
        "屏幕监控", "录制屏幕", "录屏", "开始监控", "停止监控",
        "screen record", "screenpipe", "监控屏幕", "查看最近屏幕"
    ]
    priority = 8

    def run(self, text: str = "", **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        t = text.lower()
        if any(w in t for w in ["停止", "结束", "stop"]):
            action = "stop"
        elif any(w in t for w in ["最近", "回放", "recent"]):
            action = "recent"
        elif any(w in t for w in ["状态", "status"]):
            action = "status"
        elif any(w in t for w in ["开始", "启动", "录制", "监控", "record", "start", "monitor"]):
            action = "start"
        else:
            action = action or "status"

        mode = kwargs.get("mode", "screen")
        if "音频" in text or "声音" in text or "audio" in t:
            mode = "audio"
        elif "屏幕" in text or "画面" in text or "screen" in t or "vision" in t:
            mode = "screen"

        try:
            if action == "start":
                data = start(mode=mode, interval=kwargs.get("interval", 2.0))
                return SkillResult(data["ok"], data=data, message="已开始 24/7 监控" if data["ok"] else data.get("status", ""))
            if action == "stop":
                data = stop()
                return SkillResult(True, data=data, message="已停止监控")
            if action == "recent":
                data = recent(limit=kwargs.get("limit", 10))
                return SkillResult(data["ok"], data=data)
            data = status()
            return SkillResult(True, data=data)
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(ScreenpipeMonitorSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "状态"
    res = ScreenpipeMonitorSkill().run(query)
    print(res.to_dict())
