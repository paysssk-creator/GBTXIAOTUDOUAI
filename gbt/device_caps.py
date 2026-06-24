"""
device_caps.py — GBT 设备能力探测与调用封装

所有可能阻塞硬件驱动的调用（蓝牙扫描、摄像头读取、麦克风录制）
均在独立后台线程中执行，并带有硬超时保护，避免卡死 Flask 请求。
"""
import os
import sys
import time
import logging
import subprocess
import concurrent.futures
from typing import Dict, List, Any, Callable

L = logging.getLogger("GBT.DeviceCaps")

# 全局线程池，所有设备 IO 均通过它执行，避免阻塞主请求线程
_DEVICE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="gbt_device"
)


def _run_with_timeout(
    fn: Callable, timeout: float, *args, **kwargs
) -> Any:
    """在后台线程执行函数，超时返回 TimeoutError 包装。"""
    future = _DEVICE_EXECUTOR.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        try:
            future.exception(timeout=0.2)
        except Exception:
            pass
        raise TimeoutError(f"设备调用超时（{timeout}s）")


def _safe_run(cmd: List[str], timeout: int = 15) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors='replace')
        return {"ok": True, "returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def probe_voice() -> Dict[str, Any]:
    """语音输出能力：检查 Windows TTS / edge-tts 可用性"""
    result = {"available": False, "methods": []}
    try:
        ps = '''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SpeakAsyncCancelAll()
[System.Reflection.Assembly]::LoadWithPartialName("System.Speech") | Out-Null
Write-Output "OK"
'''
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, timeout=5, errors='replace')
        if r.returncode == 0 and "OK" in r.stdout:
            result["methods"].append("system.speech")
    except Exception as e:
        L.debug(f"System.Speech probe: {e}")

    try:
        import edge_tts
        result["methods"].append("edge_tts")
    except Exception as e:
        L.debug(f"edge_tts probe: {e}")

    result["available"] = len(result["methods"]) > 0
    return result


def _probe_microphone_native() -> Dict[str, Any]:
    """麦克风原生探测（在线程中执行）"""
    result = {"available": False, "devices": []}
    import pyaudio
    pa = pyaudio.PyAudio()
    try:
        default_input = pa.get_default_input_device_info()
        result["default_input"] = {
            "index": default_input["index"],
            "name": default_input["name"],
            "channels": default_input["maxInputChannels"],
            "rate": default_input["defaultSampleRate"],
        }
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                result["devices"].append({
                    "index": i,
                    "name": info.get("name"),
                    "channels": info.get("maxInputChannels"),
                    "rate": info.get("defaultSampleRate"),
                })
        result["available"] = True
    finally:
        pa.terminate()
    return result


def probe_microphone() -> Dict[str, Any]:
    """麦克风能力：检查 pyaudio 与默认输入设备（带超时）"""
    try:
        return _run_with_timeout(_probe_microphone_native, timeout=4.0)
    except Exception as e:
        return {"available": False, "devices": [], "error": str(e)}


def _probe_bluetooth_native() -> Dict[str, Any]:
    """蓝牙原生探测（在线程中执行）"""
    result = {"available": False, "adapter_ok": False, "devices": []}
    import asyncio
    from bleak import BleakScanner

    async def _scan():
        devices = await BleakScanner.discover(timeout=3.0)
        return [{"address": d.address, "name": d.name or "Unknown"} for d in devices]

    result["available"] = True
    result["library"] = "bleak"
    try:
        # bleak 在 Windows 上依赖 asyncio 事件循环，在线程里新建 loop 避免与主线程冲突
        result["devices"] = asyncio.run(_scan())
        result["adapter_ok"] = True
    except Exception as e:
        result["adapter_error"] = str(e)
    return result


def probe_bluetooth() -> Dict[str, Any]:
    """蓝牙能力：检查 bleak 可用性并列出附近设备（带超时）"""
    try:
        return _run_with_timeout(_probe_bluetooth_native, timeout=5.0)
    except Exception as e:
        return {"available": False, "adapter_ok": False, "devices": [], "error": str(e)}


def probe_wifi() -> Dict[str, Any]:
    """WiFi / 无线网络能力：Windows 下读取可用网络列表"""
    result = {"available": False, "networks": []}
    if sys.platform != "win32":
        result["error"] = "WiFi probe only implemented on Windows"
        return result
    try:
        ps = '''
$profiles = netsh wlan show profiles 2>$null
$connected = netsh wlan show interfaces 2>$null | Select-String "SSID" | Select-Object -First 1
Write-Output "PROFILES"
$profiles
Write-Output "CONNECTED"
$connected
'''
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, timeout=8, errors='replace')
        if r.returncode == 0:
            result["available"] = True
            result["raw"] = r.stdout
            for line in r.stdout.splitlines():
                line = line.strip()
                if ":" in line and "所有用户配置文件" in line:
                    result["networks"].append(line.split(":", 1)[1].strip())
                elif ":" in line and "配置文件" in line and "所有" not in line:
                    result["networks"].append(line.split(":", 1)[1].strip())
    except Exception as e:
        result["error"] = str(e)
    return result


def _probe_camera_native() -> Dict[str, Any]:
    """摄像头原生探测（在线程中执行）"""
    result = {"available": False, "devices": []}
    import cv2
    result["library"] = "opencv"
    for idx in range(3):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)  # DirectShow 在 Windows 上更稳定
        if cap.isOpened():
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            cap.release()
            result["devices"].append({"index": idx, "width": width, "height": height})
        else:
            cap.release()
    result["available"] = len(result["devices"]) > 0
    return result


def probe_camera() -> Dict[str, Any]:
    """摄像头能力：检查 OpenCV 是否可枚举摄像头设备（带超时）"""
    try:
        return _run_with_timeout(_probe_camera_native, timeout=5.0)
    except Exception as e:
        return {"available": False, "devices": [], "error": str(e)}


def probe_screen() -> Dict[str, Any]:
    """屏幕能力：分辨率与截图可用性"""
    result = {"available": False, "resolution": None}
    try:
        import pyautogui
        result["resolution"] = {"width": pyautogui.size().width, "height": pyautogui.size().height}
        result["available"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


def probe_keyboard_mouse() -> Dict[str, Any]:
    """键鼠控制能力：检查 pyautogui / pydirectinput / ahk 可用性"""
    result = {"available": False, "methods": []}
    try:
        import pyautogui
        result["methods"].append("pyautogui")
    except Exception as e:
        L.debug(f"pyautogui probe: {e}")
    try:
        import pydirectinput
        result["methods"].append("pydirectinput")
    except Exception as e:
        L.debug(f"pydirectinput probe: {e}")
    try:
        import ahk
        result["methods"].append("ahk")
    except Exception as e:
        L.debug(f"ahk probe: {e}")
    result["available"] = len(result["methods"]) > 0
    return result


def probe_notifications() -> Dict[str, Any]:
    """桌面通知能力：检查 win10toast / System.Windows.Forms 可用性"""
    result = {"available": False, "methods": []}
    try:
        import win10toast
        result["methods"].append("win10toast")
    except Exception as e:
        L.debug(f"win10toast probe: {e}")
    try:
        ps = '''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.NotifyIcon]::new() | Out-Null
Write-Output "OK"
'''
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, timeout=5, errors='replace')
        if r.returncode == 0 and "OK" in r.stdout:
            result["methods"].append("system.windows.forms")
    except Exception as e:
        L.debug(f"System.Windows.Forms probe: {e}")
    result["available"] = len(result["methods"]) > 0
    return result


def probe_all() -> Dict[str, Any]:
    """一次性探测所有设备能力，各能力并行探测。"""
    t0 = time.time()
    probes = {
        "voice": probe_voice,
        "microphone": probe_microphone,
        "bluetooth": probe_bluetooth,
        "wifi": probe_wifi,
        "camera": probe_camera,
        "screen": probe_screen,
        "keyboard_mouse": probe_keyboard_mouse,
        "notifications": probe_notifications,
    }
    results = {}
    # 限制并发探测线程数，避免多请求同时触发时线程/设备资源争用
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(probes), 4)) as pool:
        future_to_name = {pool.submit(fn): name for name, fn in probes.items()}
        for future in concurrent.futures.as_completed(future_to_name, timeout=20):
            name = future_to_name[future]
            try:
                results[name] = future.result(timeout=2)
            except Exception as e:
                results[name] = {"available": False, "error": str(e)}
    results["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
    return results


def safe_speak(text: str) -> Dict[str, Any]:
    """安全调用语音输出"""
    try:
        from gbt.desktop_ctl import desktop_ctl
        return desktop_ctl.speak(text)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def safe_notify(title: str, message: str) -> Dict[str, Any]:
    """安全调用桌面通知"""
    try:
        from gbt.desktop_ctl import desktop_ctl
        return desktop_ctl.notify(title, message)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _camera_snapshot_native(index: int, save_path: str = None) -> Dict[str, Any]:
    """摄像头拍照原生实现（在线程中执行）"""
    import cv2
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        return {"ok": False, "error": f"摄像头 {index} 无法打开"}
    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            return {"ok": False, "error": "读取摄像头画面失败"}
        if save_path:
            cv2.imwrite(save_path, frame)
        _, buf = cv2.imencode(".jpg", frame)
        import base64
        b64 = base64.b64encode(buf.tobytes()).decode()
        return {
            "ok": True,
            "index": index,
            "resolution": frame.shape[:2],
            "base64_preview": b64[:200] + "...",
            "save_path": save_path,
        }
    finally:
        cap.release()


def safe_camera_snapshot(index: int = 0, save_path: str = None) -> Dict[str, Any]:
    """安全拍摄单张摄像头画面（带超时）"""
    try:
        return _run_with_timeout(_camera_snapshot_native, timeout=5.0, index=index, save_path=save_path)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _audio_record_native(seconds: float, save_path: str = None) -> Dict[str, Any]:
    """麦克风录制原生实现（在线程中执行）"""
    import pyaudio
    import wave
    pa = pyaudio.PyAudio()
    try:
        info = pa.get_default_input_device_info()
        rate = int(info["defaultSampleRate"])
        channels = min(2, int(info["maxInputChannels"])) or 1
        chunk = 1024
        fmt = pyaudio.paInt16
        frames = []
        stream = pa.open(format=fmt, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
        try:
            for _ in range(0, int(rate / chunk * seconds)):
                frames.append(stream.read(chunk, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()
        path = save_path or os.path.join(os.environ.get("GBT_HOME", os.getcwd()), "mic_test.wav")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(pa.get_sample_size(fmt))
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))
        return {"ok": True, "path": path, "duration": seconds, "rate": rate, "channels": channels}
    finally:
        pa.terminate()


def safe_audio_record(seconds: float = 3.0, save_path: str = None) -> Dict[str, Any]:
    """安全录制麦克风音频（WAV 格式，带超时）"""
    timeout = max(seconds + 2.0, 5.0)
    try:
        return _run_with_timeout(_audio_record_native, timeout=timeout, seconds=seconds, save_path=save_path)
    except Exception as e:
        return {"ok": False, "error": str(e)}
