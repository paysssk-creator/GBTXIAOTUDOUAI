"""Patch winctl.py to add edge-tts voice support"""
import sys
sys.path.insert(0, r"C:\Users\ADMIN\GBTXIAOTUDOUAI")

src_path = r"C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt\winctl.py"
with open(src_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add tempfile to imports
content = content.replace(
    "import os, subprocess, base64, threading, asyncio, logging",
    "import os, subprocess, base64, threading, asyncio, logging, tempfile",
    1
)

# 2. Add voice config after L = logging.getLogger(...)
old = 'L = logging.getLogger("GBT.WinCtl")'
new = '''L = logging.getLogger("GBT.WinCtl")

# ── 语音引擎配置: 晓晓御姐温柔音 ──
VOICE_EDGE_TTS = {
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "-10%",
    "pitch": "-5Hz",
}
VOICE_PYTTSX3 = {
    "voice_name": "Huihui",
    "rate": 160,
}
'''
content = content.replace(old, new, 1)

# 3. Replace _voice_speak with edge-tts primary + pyttsx3/SAPI fallback
old_speak = '''    def _voice_speak(self, text: str="", rate: int=180) -> WinResult:
        try:
            import pyttsx3
            e = pyttsx3.init(); e.setProperty("rate", rate)
            e.say(text); e.runAndWait()
            return WinResult(True,"voice","speak",data=f"播放:{text[:50]}")
        except Exception as e:
            L.debug(f"pyttsx3 不可用，降级 SAPI: {e}")
            self._ps(f'Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")')
            return WinResult(True,"voice","speak",data=f"SAPI:{text[:50]}")'''

new_speak = '''    def _voice_speak(self, text: str="", rate: int=180) -> WinResult:
        """语音合成: edge-tts晓晓御姐音 > pyttsx3慧慧 > SAPI降级"""
        # ── 首选: edge-tts 晓晓御姐温柔音 ──
        try:
            import edge_tts as _etts
            cfg = VOICE_EDGE_TTS
            tmp = os.path.join(tempfile.gettempdir(), f"gbt_tts_{os.getpid()}.mp3")

            async def _gen():
                c = _etts.Communicate(text, voice=cfg["voice"],
                                      rate=cfg["rate"], pitch=cfg["pitch"])
                await c.save(tmp)

            asyncio.run(_gen())
            if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
                subprocess.Popen(
                    ["powershell", "-c",
                     f'(New-Object Media.SoundPlayer "{tmp}").PlaySync(); Remove-Item "{tmp}"'],
                    creationflags=0x08000000  # CREATE_NO_WINDOW
                )
                return WinResult(True, "voice", "speak",
                                 data=f"晓晓御姐音:{text[:40]}")
        except Exception as e:
            L.debug(f"edge-tts 不可用: {e}")

        # ── 降级: pyttsx3 慧慧中文女声 ──
        try:
            import pyttsx3
            e = pyttsx3.init()
            cfg = VOICE_PYTTSX3
            e.setProperty("rate", cfg.get("rate", 160))
            voices = e.getProperty("voices")
            for v in voices:
                if cfg["voice_name"].lower() in v.name.lower():
                    e.setProperty("voice", v.id)
                    break
            e.say(text)
            e.runAndWait()
            return WinResult(True, "voice", "speak",
                             data=f"慧慧:{text[:40]}")
        except Exception as e:
            L.debug(f"pyttsx3 不可用，降级 SAPI: {e}")
            self._ps(f'Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")')
            return WinResult(True, "voice", "speak",
                             data=f"SAPI:{text[:40]}")'''

content = content.replace(old_speak, new_speak, 1)

with open(src_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Voice module fully patched - edge-tts + pyttsx3 + SAPI")

