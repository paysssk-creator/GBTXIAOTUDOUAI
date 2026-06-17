"""
winctl.py — 原生Windows操控引擎
屏幕/语音/蓝牙/WiFi/键鼠/进程/窗口实时调用
"""

import os, subprocess, base64, threading, asyncio
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

class WinFeature(Enum):
    SCREEN="screen"; VOICE="voice"; BLUETOOTH="bt"; WIFI="wifi"
    PROCESS="proc"; WINDOW="window"; VOLUME="volume"
    CLIPBOARD="clip"; NOTIFY="notify"; LOCK="lock"
    SHUTDOWN="shutdown"; KEYBOARD="keyboard"; MOUSE="mouse"
    CAMERA="camera"; OCR="ocr"

@dataclass
class WinResult:
    ok: bool; feature: str; action: str
    data: str=""; error: str=""


class WindowsController:

    def __init__(self):
        self._f = {f.value: True for f in WinFeature}
        print(f"🖥️ WinCtl: {len(self._f)}能力")

    def call(self, f: str, a: str, **kw) -> WinResult:
        m = getattr(self, f"_{f}_{a}".replace("-","_"), None)
        if not m: return WinResult(False, f, a, error=f"未知:{f}.{a}")
        try: return m(**kw)
        except Exception as e: return WinResult(False, f, a, error=str(e))

    def _ps(self, cmd: str) -> str:
        r = subprocess.run(f'powershell -c "{cmd}"', shell=True,
            capture_output=True, text=True, timeout=15)
        return r.stdout.strip()[:2000] or r.stderr.strip()[:500]

    # ── 屏幕 ──
    def _screen_capture(self, region: str="") -> WinResult:
        try:
            from PIL import ImageGrab; import io
            if region:
                x,y,w,h = map(int, region.split(","))
                img = ImageGrab.grab(bbox=(x,y,x+w,y+h))
            else: img = ImageGrab.grab()
            buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True)
            return WinResult(True,"screen","capture",
                data=f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}")
        except ImportError:
            return WinResult(False,"screen","capture",error="pip install Pillow")

    def _screen_info(self) -> WinResult:
        try:
            from screeninfo import get_monitors
            ms = [f"{m.name}:{m.width}x{m.height}" for m in get_monitors()]
            return WinResult(True,"screen","info",data="\n".join(ms))
        except: return WinResult(True,"screen","info",data=self._ps("Get-WmiObject Win32_VideoController|Select Name,CurrentHorizontalResolution"))

    # ── 键鼠 ──
    def _keyboard_type(self, text: str="") -> WinResult:
        try: import pyautogui; pyautogui.write(text, interval=0.02)
        except: self._ps(f'(New-Object -ComObject WScript.Shell).SendKeys("{text}")')
        return WinResult(True,"keyboard","type",data=f"输入{len(text)}字")

    def _keyboard_hotkey(self, keys: str="") -> WinResult:
        try: import pyautogui; pyautogui.hotkey(*keys.split("+"))
        except: return WinResult(False,"keyboard","hotkey",error="pip install pyautogui")
        return WinResult(True,"keyboard","hotkey",data=keys)

    def _mouse_move(self, x: int=0, y: int=0) -> WinResult:
        try: import pyautogui; pyautogui.moveTo(x,y)
        except: self._ps(f"[System.Windows.Forms.Cursor]::Position=New-Object System.Drawing.Point({x},{y})")
        return WinResult(True,"mouse","move",data=f"({x},{y})")

    def _mouse_click(self, button: str="left") -> WinResult:
        try: import pyautogui; pyautogui.click(button=button)
        except: return WinResult(False,"mouse","click",error="pip install pyautogui")
        return WinResult(True,"mouse","click",data=button)

    # ── 语音/音频 ──
    def _voice_listen(self, dur: int=5, lang: str="zh-CN") -> WinResult:
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as s:
                r.adjust_for_ambient_noise(s, 1)
                print(f"🎤 监听{dur}s...")
                audio = r.listen(s, timeout=dur, phrase_time_limit=dur)
            try: txt = r.recognize_google(audio, language=lang)
            except: txt = r.recognize_sphinx(audio)
            return WinResult(True,"voice","listen",data=txt)
        except ImportError:
            return WinResult(False,"voice","listen",error="pip install SpeechRecognition pyaudio")
        except Exception as e: return WinResult(False,"voice","listen",error=str(e))

    def _voice_speak(self, text: str="", rate: int=180) -> WinResult:
        try:
            import pyttsx3
            e = pyttsx3.init(); e.setProperty("rate", rate)
            e.say(text); e.runAndWait()
            return WinResult(True,"voice","speak",data=f"播放:{text[:50]}")
        except:
            self._ps(f'Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")')
            return WinResult(True,"voice","speak",data=f"SAPI:{text[:50]}")

    def _volume_get(self) -> WinResult:
        try:
            from ctypes import cast,POINTER; from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
            d = AudioUtilities.GetSpeakers().Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None)
            v = cast(d,POINTER(IAudioEndpointVolume)).GetMasterVolumeLevelScalar()
            return WinResult(True,"volume","get",data=f"{int(v*100)}%")
        except: return WinResult(True,"volume","get",data=self._ps("(Get-AudioDevice -Playback).Volume"))

    def _volume_set(self, level: int=50) -> WinResult:
        try:
            from ctypes import cast,POINTER; from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
            d = AudioUtilities.GetSpeakers().Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None)
            cast(d,POINTER(IAudioEndpointVolume)).SetMasterVolumeLevelScalar(level/100,None)
        except: pass
        return WinResult(True,"volume","set",data=f"{level}%")

    # ── 摄像头 ──
    def _camera_capture(self) -> WinResult:
        try:
            import cv2
            cam = cv2.VideoCapture(0); ret, frame = cam.read(); cam.release()
            if ret:
                _, buf = cv2.imencode(".jpg", frame)
                return WinResult(True,"camera","capture",
                    data=f"data:image/jpeg;base64,{base64.b64encode(buf.tobytes()).decode()}")
            return WinResult(False,"camera","capture",error="无画面")
        except: return WinResult(False,"camera","capture",error="pip install opencv-python")

    # ── 进程/窗口 ──
    def _proc_list(self, filter: str="") -> WinResult:
        c = f"tasklist /fo csv /nh" + (f' /fi "IMAGENAME eq {filter}*"' if filter else "")
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=10)
        ps = [p.split(",")[0].strip('"') for p in r.stdout.strip().split("\n") if p.strip()][:30]
        return WinResult(True,"proc","list",data="\n".join(ps))

    def _proc_kill(self, name: str="") -> WinResult:
        subprocess.run(f"taskkill /f /im {name}", shell=True, capture_output=True, timeout=10)
        return WinResult(True,"proc","kill",data=name)

    def _proc_start(self, path: str="") -> WinResult:
        subprocess.Popen(path, shell=True)
        return WinResult(True,"proc","start",data=path)

    def _window_list(self) -> WinResult:
        r = subprocess.run('powershell -c "Get-Process|Where{$_.MainWindowTitle}|Select MainWindowTitle,Id"',
            shell=True, capture_output=True, text=True, timeout=10)
        ws = [l.strip() for l in r.stdout.split("\n") if l.strip()][1:15]
        return WinResult(True,"window","list",data="\n".join(ws))

    def _window_focus(self, title: str="") -> WinResult:
        self._ps(f'Add-Type @"using System.Runtime.InteropServices;public class W{{[DllImport(\"user32\")]public static extern IntPtr FindWindow(string a,string b);[DllImport(\"user32\")]public static extern bool SetForegroundWindow(IntPtr h);}}"@;[W]::SetForegroundWindow([W]::FindWindow(null,"{title}"))')
        return WinResult(True,"window","focus",data=title)

    # ── WiFi ──
    def _wifi_list(self) -> WinResult:
        r = subprocess.run("netsh wlan show networks mode=bssid",
            shell=True, capture_output=True, text=True, timeout=15)
        ss = [l.split(":")[1].strip() for l in r.stdout.split("\n") if "SSID" in l and "BSSID" not in l]
        return WinResult(True,"wifi","list",data="\n".join(ss[:20]) if ss else "无可用网络")

    def _wifi_connect(self, ssid: str="", pwd: str="") -> WinResult:
        xml = f'<?xml version="1.0"?><WLANProfile xmlns="..."><name>{ssid}</name><SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig><connectionType>ESS</connectionType><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption></authEncryption><sharedKey><keyMaterial>{pwd}</keyMaterial></sharedKey></security></MSM></WLANProfile>'
        fp = os.path.join(os.environ.get("TEMP","."), f"gbt_wifi.xml")
        with open(fp,"w") as f: f.write(xml)
        subprocess.run(f'netsh wlan add profile filename="{fp}"', shell=True, capture_output=True, timeout=10)
        subprocess.run(f'netsh wlan connect name="{ssid}"', shell=True, capture_output=True, timeout=15)
        os.remove(fp) if os.path.exists(fp) else None
        return WinResult(True,"wifi","connect",data=ssid)

    def _wifi_status(self) -> WinResult:
        r = subprocess.run("netsh wlan show interfaces", shell=True, capture_output=True, text=True, timeout=10)
        info = {}
        for l in r.stdout.split("\n"):
            l = l.strip()
            if "SSID" in l and "BSSID" not in l: info["ssid"] = l.split(":")[-1].strip()
            if "Signal" in l: info["signal"] = l.split(":")[-1].strip()
            if "State" in l: info["state"] = l.split(":")[-1].strip()
        return WinResult(True,"wifi","status",data=str(info) if info else "未连接")

    def _wifi_disconnect(self) -> WinResult:
        subprocess.run("netsh wlan disconnect", shell=True, capture_output=True, timeout=10)
        return WinResult(True,"wifi","disconnect",data="已断开")

    # ── 蓝牙 ──
    def _bt_list(self) -> WinResult:
        r = subprocess.run('powershell -c "Get-PnpDevice -Class Bluetooth|Where Status -eq OK|Select FriendlyName"',
            shell=True, capture_output=True, text=True, timeout=15)
        ds = [l.strip() for l in r.stdout.split("\n") if l.strip()][1:21]
        return WinResult(True,"bt","list",data="\n".join(ds) if ds else "无设备")

    def _bt_scan(self, timeout: int=10) -> WinResult:
        try:
            from bleak import BleakScanner
            async def s(): return await BleakScanner.discover(timeout=timeout)
            ds = asyncio.run(s())
            info = [f"{d.name or '?'}: {d.address} RSSI:{d.rssi}" for d in ds]
            return WinResult(True,"bt","scan",data="\n".join(info) if info else "未发现")
        except ImportError: return WinResult(False,"bt","scan",error="pip install bleak")
        except: return self._bt_list()

    def _bt_status(self) -> WinResult:
        r = subprocess.run('powershell -c "Get-PnpDevice -Class Bluetooth|Select Status,FriendlyName"',
            shell=True, capture_output=True, text=True, timeout=10)
        return WinResult(True,"bt","status",data=r.stdout[:1000])

    # ── 系统 ──
    def _lock_do(self) -> WinResult:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return WinResult(True,"lock","do",data="已锁定")

    def _shutdown_do(self, delay: int=0) -> WinResult:
        subprocess.run(f"shutdown /s /t {delay}", shell=True)
        return WinResult(True,"shutdown","do",data=f"{delay}s后关机")

    def _shutdown_cancel(self) -> WinResult:
        subprocess.run("shutdown /a", shell=True)
        return WinResult(True,"shutdown","cancel",data="已取消")

    def _notify_show(self, title: str="", msg: str="") -> WinResult:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, msg, duration=5, threaded=True)
        except: pass
        return WinResult(True,"notify","show",data=title)

    def _clipboard_get(self) -> WinResult:
        try: import pyperclip; return WinResult(True,"clip","get",data=pyperclip.paste())
        except: return WinResult(False,"clip","get",error="pip install pyperclip")

    def _clipboard_set(self, text: str="") -> WinResult:
        try: import pyperclip; pyperclip.copy(text)
        except: return WinResult(False,"clip","set",error="pip install pyperclip")
        return WinResult(True,"clip","set",data=f"复制{len(text)}字")

    # ── OCR ──
    def _ocr_image(self, image: str="") -> WinResult:
        """图片转文字"""
        try:
            from .ocr import image_to_text
            r = image_to_text(image)
            return WinResult(True, "ocr", "image",
                data=f"[{r.engine.value}引擎 | {r.duration:.1f}s]\n{r.text[:3000]}")
        except Exception as e:
            return WinResult(False, "ocr", "image", error=str(e))

    def _ocr_screen(self) -> WinResult:
        """截图+OCR一键"""
        try:
            from .ocr import screenshot_to_text
            text, b64 = screenshot_to_text()
            return WinResult(True, "ocr", "screen",
                data=f"{text[:2000]}\n\n[截图base64: {len(b64)}chars]")
        except Exception as e:
            return WinResult(False, "ocr", "screen", error=str(e))

    def _ocr_region(self, x: int=0, y: int=0, w: int=100, h: int=100) -> WinResult:
        """区域截图+OCR"""
        try:
            from .ocr import ImageToText
            ocr = ImageToText()
            r = ocr.ocr_region(x, y, w, h)
            return WinResult(True, "ocr", "region",
                data=f"[{r.engine.value}]\n{r.text[:2000]}")
        except Exception as e:
            return WinResult(False, "ocr", "region", error=str(e))

    def help(self) -> str:
        a = [
            ("screen.capture", "截图"), ("keyboard.type/text", "输入"),
            ("keyboard.hotkey/keys", "快捷键"), ("mouse.move/x,y", "鼠标移动"),
            ("mouse.click/button", "点击"), ("voice.listen/dur", "语音识别"),
            ("voice.speak/text", "TTS"), ("volume.get/set", "音量"),
            ("camera.capture", "拍照"),
            ("proc.list/kill/start", "进程管理"),
            ("window.list/focus", "窗口管理"),
            ("wifi.list/connect/status/disconnect", "WiFi控制"),
            ("bt.list/scan/status", "蓝牙控制"),
            ("notify.show", "通知"), ("clipboard.get/set", "剪贴板"),
            ("lock.do", "锁屏"), ("shutdown.do/cancel", "关机"),
        ]
        return "## 🖥️ WinCtl\n" + "\n".join(f"- `{n}` — {d}" for n,d in a)


_wctl: Optional[WindowsController] = None

def get_winctl() -> WindowsController:
    global _wctl
    if _wctl is None: _wctl = WindowsController()
    return _wctl
