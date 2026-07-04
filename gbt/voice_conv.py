# -*- coding: utf-8 -*-
"""
gbt/voice_conv.py — GBT 语音对话引擎 v1.0

双向语音对话管道:
  1. 听 (STT) — 语音识别转文字
  2. 想 (Route) — 意图路由 + LLM推理
  3. 说 (TTS) — 文字合成语音播放

支持多轮对话上下文记忆
"""

import sys, os, time, json, logging, threading, queue
from typing import Optional, Callable

L = logging.getLogger("GBT.VoiceConv")

# ═══════════════════════════════════════════════════════
# STT: 语音识别 (Speech-to-Text)
# ═══════════════════════════════════════════════════════

class SpeechRecognizer:
    """语音识别 — 支持多引擎自动降级"""

    def __init__(self):
        self._engine = self._detect_engine()
        self._recognizer = None
        self._mic = None
        self._init_done = False

    def _detect_engine(self) -> str:
        """检测可用 STT 引擎"""
        # Try Windows built-in dictation (most reliable)
        if sys.platform == "win32":
            return "win32_dictation"
        # Try speech_recognition (Google Web)
        try:
            import speech_recognition as sr
            m = sr.Microphone()
            return "sr_google"
        except Exception:
            pass
        # Try Vosk (offline)
        try:
            import vosk
            return "vosk"
        except ImportError:
            pass
        return "none"

    def _ensure_init(self) -> bool:
        """延迟初始化识别器"""
        if self._init_done:
            return self._recognizer is not None
        self._init_done = True

        try:
            if self._engine in ("sr_google", "sr_sphinx"):
                import speech_recognition as sr
                self._recognizer = sr.Recognizer()
                self._mic = sr.Microphone()
                # 调整环境噪声
                with self._mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                L.info(f"STT initialized: {self._engine}")
                return True
            elif self._engine == "vosk":
                import vosk
                import pyaudio
                self._recognizer = vosk.KaldiRecognizer(None, 16000)
                return True
            elif self._engine == "win32_dictation":
                # 验证是否有可用麦克风
                import subprocess
                try:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_SoundDevice | Where-Object {$_.Name -match 'Microphone|麦克风'}).Count"],
                        capture_output=True, text=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    count = int(r.stdout.strip() or 0)
                    if count > 0:
                        self._recognizer = True
                        return True
                    L.info("无麦克风设备，STT不可用")
                    return False
                except Exception:
                    return False
        except Exception as e:
            L.warning(f"STT init failed: {e}")
            return False
        return False

    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> dict:
        """听取用户语音并返回文字"""
        if not self._ensure_init():
            return {"ok": False, "error": "无可用STT引擎", "engine": self._engine}

        try:
            if self._engine == "sr_google":
                return self._listen_sr(timeout, phrase_time_limit)
            elif self._engine == "win32_dictation":
                return self._listen_win32(timeout)
            else:
                return {"ok": False, "error": f"引擎 {self._engine} 未实现"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:120], "engine": self._engine}

    def _listen_sr(self, timeout: float, phrase_limit: float) -> dict:
        import speech_recognition as sr
        with self._mic as source:
            L.info("正在听...")
            try:
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
            except sr.WaitTimeoutError:
                return {"ok": False, "error": "未检测到语音", "text": ""}

        try:
            text = self._recognizer.recognize_google(audio, language="zh-CN")
            L.info(f"听到: {text}")
            return {"ok": True, "text": text, "engine": "sr_google"}
        except sr.UnknownValueError:
            return {"ok": False, "error": "无法识别", "text": ""}
        except sr.RequestError as e:
            # Fallback to Sphinx offline
            try:
                text = self._recognizer.recognize_sphinx(audio)
                return {"ok": True, "text": text, "engine": "sr_sphinx"}
            except Exception:
                return {"ok": False, "error": f"识别服务不可用: {e}"}

    def _listen_win32(self, timeout: float) -> dict:
        """使用 Windows 内置语音识别"""
        import subprocess
        # Use System.Speech with DictationGrammar
        ps_code = f"""
Add-Type -AssemblyName System.Speech
try {{
    $reco = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $reco.LoadGrammar($grammar)
    $reco.SetInputToDefaultAudioDevice()
    $result = $reco.Recognize([System.TimeSpan]::FromSeconds({timeout}))
    if ($result -ne $null) {{
        Write-Output $result.Text
    }} else {{
        Write-Output ''
    }}
}} catch {{
    Write-Output "ERROR:$($_.Exception.Message)"
}}
"""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code],
                capture_output=True, text=True, timeout=max(20, int(timeout + 5)),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            text = r.stdout.strip()
            if text.startswith("ERROR:"):
                return {"ok": False, "error": text[6:][:120], "text": ""}
            if text:
                return {"ok": True, "text": text, "engine": "win32_dictation"}
            return {"ok": False, "error": "未识别到语音 (请确保麦克风已连接)", "text": ""}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "识别超时", "text": ""}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}


# ═══════════════════════════════════════════════════════
# 对话管道
# ═══════════════════════════════════════════════════════

class VoiceConversation:
    """双向语音对话"""

    def __init__(self, http_base: str = "http://127.0.0.1:8765"):
        self._stt = SpeechRecognizer()
        self._http = http_base
        self._history: list = []  # 对话历史
        self._running = False
        self._on_response: Optional[Callable] = None

    def speak(self, text: str, voice: str = "xiaoxiao") -> dict:
        """TTS 语音输出"""
        try:
            from gbt.voice_tts import GBTVoice
            v = GBTVoice()
            return v.speak(text, voice=voice)
        except Exception as e:
            # Fallback: try via HTTP API
            try:
                import requests
                r = requests.post(
                    f"{self._http}/api/reason",
                    json={"text": f"说话:{text}", "mode": "quick"},
                    timeout=10
                )
                return {"ok": True, "engine": "http_fallback", "text": text}
            except Exception:
                return {"ok": False, "error": str(e)[:80]}

    def listen(self, timeout: float = 5.0) -> dict:
        """听取用户语音输入"""
        return self._stt.listen(timeout=timeout)

    def think(self, text: str) -> dict:
        """发送文字到 GBT 推理引擎"""
        try:
            import requests
            r = requests.post(
                f"{self._http}/api/reason",
                json={"text": text, "mode": "chain"},
                timeout=30
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "ok": True,
                    "conclusion": data.get("conclusion", "")[:1000],
                    "capability": data.get("capability", ""),
                    "confidence": data.get("confidence", 50),
                }
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    def round(self, prompt: str = "", listen_timeout: float = 5.0) -> dict:
        """
        一轮对话: 听→想→说
        
        如果给定 prompt，先说再听再回
        如果没有 prompt，直接听→想→说
        """
        result = {"ok": True, "steps": []}

        # Step 0: 主动说话 (如有)
        if prompt:
            L.info(f"说: {prompt}")
            sp = self.speak(prompt)
            result["steps"].append({"type": "speak", "text": prompt, "result": sp})

        # Step 1: 听
        L.info("听...")
        heard = self.listen(timeout=listen_timeout)
        result["steps"].append({"type": "listen", "result": heard})

        if not heard.get("ok") or not heard.get("text"):
            # 没听见，提示
            msg = "没有听到您的声音，能再说一次吗？"
            self.speak(msg)
            result["response"] = msg
            return result

        user_text = heard["text"]

        # Step 2: 想
        L.info(f"思考: {user_text}")
        thought = self.think(user_text)
        result["steps"].append({"type": "think", "input": user_text, "result": thought})

        # Step 3: 说
        reply = thought.get("conclusion", "")
        if not reply:
            reply = f"收到: {user_text}"
        # 截取语音回复 (不要太长)
        voice_reply = reply[:300] if len(reply) > 300 else reply
        L.info(f"回复: {voice_reply}")
        sp2 = self.speak(voice_reply)
        result["steps"].append({"type": "speak", "text": voice_reply, "result": sp2})

        result["response"] = voice_reply
        result["user_said"] = user_text

        # 存入历史
        self._history.append({"user": user_text, "reply": reply})

        return result

    def loop(self, rounds: int = 5, initial_prompt: str = ""):
        """多轮对话循环"""
        self._running = True

        if initial_prompt:
            self.round(prompt=initial_prompt)

        for i in range(rounds):
            if not self._running:
                break
            L.info(f"=== 对话轮次 {i+1} ===")
            r = self.round(listen_timeout=8.0)
            if not r.get("user_said"):
                continue

            # 检测退出
            if any(kw in (r.get("user_said") or "").lower()
                   for kw in ["退出", "再见", "拜拜", "停止", "结束"]):
                self.speak("好的，再见！")
                self._running = False
                break

        self._running = False

    def chat_text(self, text: str, voice_reply: bool = True) -> dict:
        """文字对话: 直接输入文字 → 语音回复 (无需麦克风, 不调 API 避免递归)"""
        # 构建简短回复
        if len(text) < 3:
            reply = f"你好！我是 GBT 操盘助手。有什么可以帮你的？"
        elif any(kw in text for kw in ["股票", "行情", "大盘", "A股", "操盘", "交易"]):
            reply = f"关于 {text}，让我为你查询相关信息。你可以问我具体的股票代码或市场行情。"
        elif any(kw in text for kw in ["你好", "嗨", "嘿", "hello"]):
            reply = f"你好！我是 GBT 智能操盘助手。我可以帮你查看股票行情、分析技术指标、操控电脑桌面、管理文件等。请随时告诉我你需要什么。"
        else:
            reply = f"收到: {text[:100]}。我是 GBT 操盘助手，可以帮你查行情、做分析、操控设备。请说具体需求。"
        
        # 语音回复
        if voice_reply:
            self.speak(reply)
        
        self._history.append({"user": text, "reply": reply})
        
        return {
            "ok": True,
            "user_said": text,
            "response": reply,
            "mode": "text",
        }

    def has_microphone(self) -> bool:
        """检测是否有可用麦克风"""
        return self._stt._ensure_init()

    def stop(self):
        """停止对话"""
        self._running = False

    def history(self) -> list:
        """获取对话历史"""
        return self._history

    def clear_history(self):
        """清除对话历史"""
        self._history = []


# ═══════════════════════════════════════════════════════
# 独立测试
# ═══════════════════════════════════════════════════════

def quick_test():
    """快速测试语音对话引擎"""
    conv = VoiceConversation()

    # 测试 TTS
    print("=== 测试语音输出 ===")
    r = conv.speak("你好！我是GBT语音助手。语音对话引擎启动成功。")
    print(f"  TTS: {r}")

    # 测试 STT
    print("\n=== 测试语音识别 (请说话...) ===")
    r = conv.listen(timeout=5.0)
    print(f"  STT: {r}")

    if r.get("text"):
        # 测试完整对话轮次
        print("\n=== 一键对话 ===")
        r = conv.round()
        print(f"  对话: {r.get('response', '')[:100]}")


if __name__ == "__main__":
    quick_test()
