"""
gbt/skills/voice_speak.py — Windows语音朗读输出
可独立运行: python -m gbt.skills.voice_speak "查询内容"
"""
import os, sys
from .base import Skill, SkillResult, registry


class VoiceSpeakSkill(Skill):
    name = "voice_speak"
    category = "notification"
    description = "Windows语音朗读输出"
    keywords = ['说', '朗读', '语音', '讲话', 'speak']
    priority = 5
    requires = []

    def run(self, text: str = "", **kwargs) -> SkillResult:
        try:
            from gbt.desktop_ctl import desktop_ctl
            desktop_ctl.speak(text)
            return SkillResult(True, data=result, message="语音朗读")
        except Exception as e:
            return SkillResult(False, error=str(e))


registry.register(VoiceSpeakSkill())


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Windows语音朗读输出"
    res = VoiceSpeakSkill().run(query)
    print(res.to_dict())
