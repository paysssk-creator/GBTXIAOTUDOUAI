# -*- coding: utf-8 -*-
"""
gbt/voice_tts.py — GBT 语音引擎 v2.0

三层语音架构:
  L1: Edge TTS (微软云端)    — 300+音色, 顶级中文质量, 免费
  L2: SAPI5 (Windows 本地)   — 无需网络, 微软内置语音
  L3: Piper TTS (本地开源)   — 离线, MIT 协议, 多语言

最佳中文音色排行:
  1. zh-CN-XiaoxiaoNeural       — 女声, 温柔自然 (TOP 1)
  2. zh-CN-YunxiNeural          — 男声, 沉稳专业
  3. zh-CN-XiaoyiNeural         — 女声, 活泼清晰
  4. zh-CN-YunjianNeural        — 男声, 新闻播报风
  5. zh-CN-XiaochenNeural       — 女声, 元气少女
  6. zh-CN-XiaohanNeural        — 女声, 知性温柔
"""

import os, sys, io, re, json, time, logging, subprocess, tempfile, threading
from pathlib import Path

L = logging.getLogger("GBT.Voice")

# ═══════════════════════════════════════════════════════
# 音色库
# ═══════════════════════════════════════════════════════

VOICES = {
    # ── 中文 Top 6 ──
    "xiaoxiao":   {"name": "zh-CN-XiaoxiaoNeural",   "gender": "Female", "style": "温柔自然", "description": "最适合日常交互"},
    "yunxi":      {"name": "zh-CN-YunxiNeural",      "gender": "Male",   "style": "沉稳专业", "description": "播报类首选"},
    "xiaoyi":     {"name": "zh-CN-XiaoyiNeural",     "gender": "Female", "style": "活泼清晰", "description": "提醒通知首选"},
    "yunjian":    {"name": "zh-CN-YunjianNeural",    "gender": "Male",   "style": "新闻播报", "description": "财经播报推荐"},
    "xiaochen":   {"name": "zh-CN-XiaochenNeural",   "gender": "Female", "style": "元气少女", "description": "轻快风格"},
    "xiaohan":    {"name": "zh-CN-XiaohanNeural",    "gender": "Female", "style": "知性温柔", "description": "温暖陪伴"},
    # ── 粤语 / 方言 ──
    "hkg":        {"name": "zh-HK-HiuGaaiNeural",    "gender": "Female", "style": "粤语女声", "description": "粤语播报"},
    "hkm":        {"name": "zh-HK-HiuMaanNeural",    "gender": "Female", "style": "粤语男声", "description": "粤语播报"},
    # ── 英文 ──
    "en_f":       {"name": "en-US-JennyNeural",      "gender": "Female", "style": "美式女声", "description": "英文播报"},
    "en_m":       {"name": "en-US-GuyNeural",        "gender": "Male",   "style": "美式男声", "description": "英文播报"},
}

VOICE_ALIASES = {
    "默认": "xiaoxiao", "温柔": "xiaoxiao", "女声": "xiaoxiao",
    "男声": "yunxi", "专业": "yunxi", "播报": "yunjian",
    "活泼": "xiaoyi", "提醒": "xiaoyi", "新闻": "yunjian",
    "少女": "xiaochen", "知性": "xiaohan", "粤语": "hkg",
    "英文": "en_f",
}


# ═══════════════════════════════════════════════════════
# L1: Edge TTS (微软云端 — 最佳质量)
# ═══════════════════════════════════════════════════════

def _play_audio(filepath: str, duration_sec: float = 5.0):
    """在 Windows 上播放音频文件 (支持 mp3/wav)"""
    if sys.platform == "win32":
        # 使用 Windows MediaPlayer COM (支持 mp3)
        ps = (
            "Add-Type -AssemblyName PresentationCore; "
            f"$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open('{filepath}'); "
            "$p.Play(); "
            f"Start-Sleep -Seconds {duration_sec}; "
            "$p.Close()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=max(30, int(duration_sec + 5)),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        import playsound
        playsound.playsound(filepath)


def _edge_tts_speak(text: str, voice: str = "xiaoxiao", rate: str = "+0%") -> dict:
    """使用 Edge TTS 朗读 (需要 edge-tts 包)"""
    try:
        import edge_tts
        voice_name = VOICES.get(voice, VOICES["xiaoxiao"])["name"]

        async def _speak():
            communicate = edge_tts.Communicate(text, voice_name, rate=rate)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            try:
                await communicate.save(tmp_path)
                est_duration = max(2.0, len(text) * 0.15)
                _play_audio(tmp_path, est_duration)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                loop.run_until_complete(_speak())
            else:
                loop.run_until_complete(_speak())
        except RuntimeError:
            asyncio.run(_speak())

        return {"ok": True, "engine": "edge_tts", "voice": voice}
    except ImportError:
        return {"ok": False, "error": "edge-tts 未安装", "engine": "edge_tts"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80], "engine": "edge_tts"}


def _edge_tts_stream(text: str, voice: str = "xiaoxiao") -> dict:
    """Edge TTS 流式播放 (低延迟, 边下边播)"""
    try:
        import edge_tts
        voice_name = VOICES.get(voice, VOICES["xiaoxiao"])["name"]

        comm = edge_tts.Communicate(text, voice_name)
        # 流式写入内存
        chunks = []
        for chunk in comm.stream_sync():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        if not chunks:
            return {"ok": False, "error": "无音频数据"}

        audio_data = b"".join(chunks)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name

        try:
            if sys.platform == "win32":
                _play_audio(tmp_path, max(2.0, len(text) * 0.15))
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return {"ok": True, "engine": "edge_tts_stream", "voice": voice}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


# ═══════════════════════════════════════════════════════
# L2: SAPI5 (Windows 内置 — 无需安装)
# ═══════════════════════════════════════════════════════

def _sapi5_speak(text: str, voice: str = "Microsoft Huihui Desktop", rate: int = 0) -> dict:
    """Windows SAPI5 TTS (内置, 离线可用) — 直接使用 COM"""
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Rate = max(-10, min(10, rate))
        try:
            speaker.Voice = speaker.GetVoices(f"Name={voice}").Item(0)
        except Exception:
            pass
        speaker.Speak(text)
        return {"ok": True, "engine": "sapi5", "voice": voice}
    except ImportError:
        # 降级到 PowerShell
        import base64 as b64
        safe = b64.b64encode(text.encode("utf-8")).decode("ascii")
        rate_val = max(-10, min(10, rate))
        ps = (
            f'Add-Type -AssemblyName System.Speech; '
            f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            f'$s.Rate = {rate_val}; '
            f'try {{ $s.SelectVoice("{voice}") }} catch {{}}; '
            f'$s.Speak([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("{safe}")))'
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return {"ok": True, "engine": "sapi5_ps", "voice": voice}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80], "engine": "sapi5"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80], "engine": "sapi5"}


# ═══════════════════════════════════════════════════════
# L3: Piper TTS (本地开源 — MIT 协议, 轻量)
# ═══════════════════════════════════════════════════════

def _piper_speak(text: str, model: str = "zh_CN-huayan-medium") -> dict:
    """Piper TTS 离线朗读"""
    try:
        import piper
        # 注意: piper 通常用 CLI 调用
        voice_dir = os.path.expanduser("~/.piper/voices")
        model_path = os.path.join(voice_dir, f"{model}.onnx")
        if not os.path.exists(model_path):
            return {"ok": False, "error": f"Piper模型未找到: {model}", "engine": "piper"}

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out_path = f.name

        try:
            subprocess.run(
                ["piper", "--model", model_path, "--output_file", out_path],
                input=text.encode("utf-8"),
                capture_output=True, timeout=30,
            )
            _play_audio(out_path, max(2.0, len(text) * 0.15))
        finally:
            try:
                os.unlink(out_path)
            except Exception:
                pass

        return {"ok": True, "engine": "piper", "model": model}
    except ImportError:
        return {"ok": False, "error": "piper 未安装", "engine": "piper"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80], "engine": "piper"}


# ═══════════════════════════════════════════════════════
# 统一 TTS 接口
# ═══════════════════════════════════════════════════════

class GBTVoice:
    """GBT 语音引擎 — 自动选择最佳 TTS"""

    # 备选引擎链: Edge TTS → SAPI5 → Piper
    ENGINES = ["edge_tts", "sapi5", "piper"]
    DEFAULT_VOICE = "xiaoxiao"

    def __init__(self):
        self._health: dict = {}
        self._preferred_engine: str = ""
        self._lock = threading.Lock()  # 并发保护
        self._detect_engines()

    def _detect_engines(self):
        """检测可用引擎"""
        try:
            import edge_tts
            self._health["edge_tts"] = True
        except ImportError:
            self._health["edge_tts"] = False

        self._health["sapi5"] = sys.platform == "win32"

        try:
            import piper
            self._health["piper"] = True
        except ImportError:
            self._health["piper"] = False

        available = [e for e in self.ENGINES if self._health.get(e)]
        self._preferred_engine = available[0] if available else ""

        L.info(f"语音引擎: {' | '.join(f'{e}={v}' for e,v in self._health.items())}")

    def speak(
        self,
        text: str,
        voice: str = "",
        rate: str = "+0%",
        force_engine: str = "",
    ) -> dict:
        """朗读文本 — 自动选择最佳引擎 (线程安全)"""
        if not text or not text.strip():
            return {"ok": False, "error": "文本为空"}

        with self._lock:
            return self._speak_unlocked(text, voice, rate, force_engine)

    def _speak_unlocked(
        self,
        text: str,
        voice: str,
        rate: str,
        force_engine: str,
    ) -> dict:
        # 解析语音名
        voice_id = voice or self.DEFAULT_VOICE
        voice_id = VOICE_ALIASES.get(voice_id, voice_id)
        if voice_id not in VOICES:
            voice_id = self.DEFAULT_VOICE

        engines = [force_engine] if force_engine else self.ENGINES

        for engine in engines:
            if not self._health.get(engine):
                continue

            if engine == "edge_tts":
                r = _edge_tts_speak(text, voice_id, rate)
            elif engine == "sapi5":
                r = _sapi5_speak(text)
            elif engine == "piper":
                r = _piper_speak(text)
            else:
                continue

            if r["ok"]:
                return r

        return {"ok": False, "error": "所有语音引擎不可用", "engines_checked": engines}

    def stream(self, text: str, voice: str = "xiaoxiao") -> dict:
        """流式朗读 (更低延迟)"""
        return _edge_tts_stream(text, voice)

    def say_trade_alert(self, stock_name: str, price: float, action: str):
        """播报交易提醒 (使用财经播报音色)"""
        text = f"{stock_name} 当前价格 {price:.2f} 元，建议 {action}"
        return self.speak(text, voice="yunjian", rate="-10%")

    def say_notification(self, message: str):
        """播报通知 (使用活泼通知音色)"""
        return self.speak(message, voice="xiaoyi", rate="+0%")

    def say_system(self, message: str):
        """播报系统消息 (使用专业播报音色)"""
        return self.speak(message, voice="yunxi", rate="-5%")

    def list_voices(self) -> list:
        """列出所有可用音色"""
        return [
            {"id": vid, "name": v["name"], "gender": v["gender"],
             "style": v["style"], "desc": v["description"]}
            for vid, v in VOICES.items()
        ]

    def engine_status(self) -> dict:
        return {
            "health": self._health,
            "preferred": self._preferred_engine,
            "voice_count": len(VOICES),
        }


# ── 全局单例 ──
_voice: GBTVoice = None


def get_voice() -> GBTVoice:
    global _voice
    if _voice is None:
        _voice = GBTVoice()
    return _voice


L.info("GBT Voice v2.0 已加载: Edge TTS + SAPI5 + Piper | 12+ 音色")
