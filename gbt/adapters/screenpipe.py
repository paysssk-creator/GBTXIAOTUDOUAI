"""
gbt/adapters/screenpipe.py - screenpipe 持续屏幕监控适配器
screenpipe 子模块已挂到 vendor/screenpipe。
本适配器优先调用真实 screenpipe 二进制（如果用户已编译安装），
否则使用 Python fallback 实现连续截图监控。
"""
import os, subprocess, sys, logging, time, threading, json
from typing import Dict, List
from datetime import datetime

L = logging.getLogger("GBT.Adapter.Screenpipe")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SP_DIR = os.path.join(ROOT, "vendor", "screenpipe")
SP_BIN = os.path.join(SP_DIR, "target", "release", "screenpipe.exe")

HOME = os.environ.get("USERPROFILE", os.environ.get("HOME", ROOT))
FALLBACK_DIR = os.path.join(HOME, ".gbt", "screenpipe")
FRAMES_DIR = os.path.join(FALLBACK_DIR, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

_proc = None
_monitor_thread = None
_stop_event = threading.Event()
_last_frames: List[Dict] = []


def _find_system_screenpipe() -> str:
    """Search screenpipe binary in PATH."""
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(p, "screenpipe.exe" if sys.platform == "win32" else "screenpipe")
        if os.path.exists(candidate):
            return candidate
    return ""


def is_available() -> bool:
    return bool(_find_system_screenpipe()) or os.path.exists(SP_DIR)


def _fallback_capture_loop(interval: float = 2.0):
    """Python fallback: continuously capture screenshots."""
    global _last_frames
    try:
        from mss import mss as MSS
    except Exception as e:
        L.error("mss not installed, fallback screen capture unavailable: %s", e)
        return

    with MSS() as sct:
        monitor = 1 if len(sct.monitors) > 1 else 0
        while not _stop_event.is_set():
            try:
                ts = datetime.now().isoformat()
                filename = f"frame_{ts.replace(':', '-').replace('.', '_')}.png"
                path = os.path.join(FRAMES_DIR, filename)
                sct.shot(mon=monitor, output=path)
                info = {"time": ts, "path": path, "source": "fallback"}
                _last_frames.append(info)
                if len(_last_frames) > 1000:
                    _last_frames = _last_frames[-1000:]
                L.debug("captured %s", path)
            except Exception as e:
                L.error("fallback capture error: %s", e)
            _stop_event.wait(interval)


def _scan_frames_dir(limit: int = 10) -> List[Dict]:
    """扫描 frames 目录返回最新的截图文件（二进制和 fallback 通用）"""
    frames = []
    try:
        files = []
        for name in os.listdir(FRAMES_DIR):
            if name.lower().endswith(".png"):
                path = os.path.join(FRAMES_DIR, name)
                files.append((os.path.getmtime(path), path))
        files.sort(reverse=True)
        for mtime, path in files[:limit]:
            frames.append({"time": datetime.fromtimestamp(mtime).isoformat(), "path": path, "source": "frames_dir"})
    except Exception as e:
        L.debug("scan frames dir error: %s", e)
    return frames


def start(mode: str = "screen", interval: float = 2.0) -> Dict:
    global _proc, _monitor_thread, _stop_event, _last_frames

    if _proc is not None and _proc.poll() is None:
        return {"ok": True, "status": "already_running", "pid": _proc.pid, "mode": mode}
    if _monitor_thread is not None and _monitor_thread.is_alive():
        return {"ok": True, "status": "already_running_fallback", "mode": mode}

    binary = _find_system_screenpipe() or (SP_BIN if os.path.exists(SP_BIN) else "")

    if binary:
        try:
            cmd = [binary]
            if mode == "screen":
                cmd += ["--disable-audio"]
            elif mode == "audio":
                cmd += ["--disable-vision"]
            env = os.environ.copy()
            _proc = subprocess.Popen(
                cmd,
                cwd=os.path.dirname(binary),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            time.sleep(3)
            still_running = _proc.poll() is None
            has_frames = len(_scan_frames_dir(limit=1)) > 0
            if still_running and has_frames:
                return {"ok": True, "status": "started", "pid": _proc.pid, "binary": binary, "mode": mode}
            L.warning("screenpipe binary did not produce frames or exited, using fallback")
            try:
                _proc.terminate()
                _proc.wait(timeout=1)
            except Exception:
                pass
            _proc = None
        except Exception as e:
            L.warning("screenpipe binary start failed, using fallback: %s", e)

    # Python fallback
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_fallback_capture_loop, args=(interval,), daemon=True)
    _monitor_thread.start()
    return {"ok": True, "status": "started_fallback", "mode": mode, "frames_dir": FRAMES_DIR}


def stop() -> Dict:
    global _proc, _monitor_thread, _stop_event
    result = {"ok": True}
    if _proc is not None:
        try:
            _proc.terminate()
            _proc.wait(timeout=3)
            result["binary"] = "stopped"
        except Exception as e:
            result["binary_error"] = str(e)
        _proc = None
    if _monitor_thread is not None and _monitor_thread.is_alive():
        _stop_event.set()
        _monitor_thread.join(timeout=3)
        result["fallback"] = "stopped"
        _monitor_thread = None
    return result


def status() -> Dict:
    binary_running = _proc is not None and _proc.poll() is None
    fallback_running = _monitor_thread is not None and _monitor_thread.is_alive()
    return {
        "ok": True,
        "available": is_available(),
        "binary": _find_system_screenpipe() or (SP_BIN if os.path.exists(SP_BIN) else ""),
        "binary_running": binary_running,
        "fallback_running": fallback_running,
        "running": binary_running or fallback_running,
        "frames_dir": FRAMES_DIR,
        "frame_count": len(_last_frames),
    }


def recent(limit: int = 10) -> Dict:
    # 合并 fallback 内存缓存和 frames 目录扫描结果，按时间倒序
    seen = set()
    frames = []
    for f in _last_frames[-limit * 2:][::-1]:
        key = f.get("path", "") or f.get("time", "")
        if key not in seen:
            seen.add(key)
            frames.append(f)
    for f in _scan_frames_dir(limit=limit * 2):
        key = f.get("path", "")
        if key not in seen:
            seen.add(key)
            frames.append(f)
    frames.sort(key=lambda x: x.get("time", ""), reverse=True)
    frames = frames[:limit]
    return {"ok": True, "frames": frames, "count": len(frames)}
