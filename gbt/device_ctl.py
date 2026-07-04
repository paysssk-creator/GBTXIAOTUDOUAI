# -*- coding: utf-8 -*-
"""
gbt/device_ctl.py — GBT 设备操控引擎 v1.0

统一操控:
  键盘  — 单键/组合键/文本输入/热键宏
  鼠标  — 移动/点击/双击/拖拽/滚轮/右键菜单
  桌面  — 窗口管理/分辨率/多显示器/应用启动
  蓝牙  — BLE 设备发现/连接/数据读写 (实验性)
"""

import os, sys, time, math, logging, subprocess
from typing import Optional, Tuple, List, Dict

L = logging.getLogger("GBT.DeviceCtl")

# ═══════════════════════════════════════════════════════
# 键盘控制
# ═══════════════════════════════════════════════════════

class KeyboardCtl:
    """键盘控制 — 单键/组合键/文本输入"""

    @staticmethod
    def press(key: str) -> dict:
        """按下并释放单键"""
        try:
            import pyautogui
            pyautogui.press(key)
            return {"ok": True, "key": key}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def hotkey(*keys: str) -> dict:
        """组合键 (如 Ctrl+C)"""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"ok": True, "hotkey": "+".join(keys)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def typewrite(text: str, interval: float = 0.02) -> dict:
        """逐字输入文本 (模拟打字)"""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            return {"ok": True, "len": len(text)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def key_down(key: str) -> dict:
        """按下并保持"""
        try:
            import pyautogui
            pyautogui.keyDown(key)
            return {"ok": True, "key": key, "state": "down"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def key_up(key: str) -> dict:
        """释放按键"""
        try:
            import pyautogui
            pyautogui.keyUp(key)
            return {"ok": True, "key": key, "state": "up"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    # ── 操盘快捷键 ──
    @staticmethod
    def copy():
        return KeyboardCtl.hotkey("ctrl", "c")

    @staticmethod
    def paste():
        return KeyboardCtl.hotkey("ctrl", "v")

    @staticmethod
    def select_all():
        return KeyboardCtl.hotkey("ctrl", "a")

    @staticmethod
    def enter():
        return KeyboardCtl.press("enter")

    @staticmethod
    def tab():
        return KeyboardCtl.press("tab")

    @staticmethod
    def esc():
        return KeyboardCtl.press("esc")

    @staticmethod
    def alt_tab():
        return KeyboardCtl.hotkey("alt", "tab")

    @staticmethod
    def win_d():
        return KeyboardCtl.hotkey("win", "d")

    @staticmethod
    def win_r():
        return KeyboardCtl.hotkey("win", "r")

    @staticmethod
    def screenshot_shortcut():
        return KeyboardCtl.hotkey("win", "shift", "s")


# ═══════════════════════════════════════════════════════
# 鼠标控制
# ═══════════════════════════════════════════════════════

class MouseCtl:
    """鼠标控制 — 移动/点击/拖拽/滚轮"""

    @staticmethod
    def move(x: int, y: int, duration: float = 0.3) -> dict:
        """移动鼠标到指定坐标"""
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            return {"ok": True, "x": x, "y": y}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def move_rel(dx: int, dy: int, duration: float = 0.1) -> dict:
        """相对移动"""
        try:
            import pyautogui
            pyautogui.moveRel(dx, dy, duration=duration)
            pos = pyautogui.position()
            return {"ok": True, "x": pos.x, "y": pos.y}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def click(x: int = None, y: int = None, button: str = "left", clicks: int = 1) -> dict:
        """点击"""
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks)
            else:
                pyautogui.click(button=button, clicks=clicks)
            return {"ok": True, "button": button, "clicks": clicks}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def double_click(x: int = None, y: int = None) -> dict:
        """双击"""
        return MouseCtl.click(x, y, clicks=2)

    @staticmethod
    def right_click(x: int = None, y: int = None) -> dict:
        """右键点击"""
        return MouseCtl.click(x, y, button="right")

    @staticmethod
    def drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> dict:
        """拖拽"""
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y, duration=0.1)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            return {"ok": True, "from": (start_x, start_y), "to": (end_x, end_y)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def scroll(clicks: int, x: int = None, y: int = None) -> dict:
        """滚轮滚动 (正=向上, 负=向下)"""
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.scroll(clicks)
            return {"ok": True, "clicks": clicks}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def position() -> dict:
        """获取当前鼠标位置"""
        try:
            import pyautogui
            pos = pyautogui.position()
            return {"ok": True, "x": pos.x, "y": pos.y}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def screen_size() -> dict:
        """获取屏幕尺寸"""
        try:
            import pyautogui
            s = pyautogui.size()
            return {"ok": True, "width": s.width, "height": s.height}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def find_and_click(image_path: str, confidence: float = 0.8) -> dict:
        """图像识别定位并点击"""
        try:
            import pyautogui
            loc = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if loc is None:
                return {"ok": False, "error": "未找到匹配图像"}
            center = pyautogui.center(loc)
            pyautogui.click(center)
            return {"ok": True, "x": center.x, "y": center.y}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}


# ═══════════════════════════════════════════════════════
# 桌面控制
# ═══════════════════════════════════════════════════════

class DesktopCtl:
    """桌面控制 — 窗口/显示器/应用"""

    @staticmethod
    def active_window_title() -> dict:
        """获取当前活动窗口标题"""
        try:
            import pyautogui
            w = pyautogui.getActiveWindow()
            if w:
                return {"ok": True, "title": w.title, "left": w.left, "top": w.top,
                        "width": w.width, "height": w.height}
            return {"ok": False, "error": "无法获取活动窗口"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def list_windows() -> dict:
        """列出所有可见窗口"""
        try:
            import pyautogui
            titles = pyautogui.getAllTitles()
            return {"ok": True, "count": len(titles), "titles": titles[:30]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def find_window(title_keyword: str) -> dict:
        """查找窗口"""
        try:
            import pyautogui
            titles = pyautogui.getAllTitles()
            matched = [t for t in titles if title_keyword.lower() in t.lower()]
            return {"ok": True, "found": len(matched), "titles": matched[:10]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def open_app(app_name: str) -> dict:
        """启动应用程序"""
        try:
            import pyautogui
            pyautogui.hotkey("win", "r")
            time.sleep(0.3)
            pyautogui.typewrite(app_name, interval=0.05)
            pyautogui.press("enter")
            return {"ok": True, "app": app_name}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def lock_screen() -> dict:
        """锁屏"""
        try:
            KeyboardCtl.hotkey("win", "l")
            return {"ok": True, "action": "lock"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def volume_up() -> dict:
        """音量+"""
        return KeyboardCtl.press("volumeup")

    @staticmethod
    def volume_down() -> dict:
        """音量-"""
        return KeyboardCtl.press("volumedown")

    @staticmethod
    def volume_mute() -> dict:
        """静音"""
        return KeyboardCtl.press("volumemute")


# ═══════════════════════════════════════════════════════
# 蓝牙控制 (经典蓝牙 + BLE) — v2.0
# ═══════════════════════════════════════════════════════

class BluetoothCtl:
    """蓝牙控制 — 经典蓝牙扫描/配对/连接 + BLE + 音频"""

    # ── 经典蓝牙扫描 (Windows) ──

    _BT_SCRIPT = os.path.join(os.path.dirname(__file__), "bt_scan.ps1")

    @staticmethod
    def classic_scan(timeout: float = 8.0) -> dict:
        """扫描经典蓝牙设备"""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", BluetoothCtl._BT_SCRIPT, "-Mode", "scan"],
                capture_output=True, timeout=max(15, int(timeout) + 5),
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = [l for l in r.stdout.strip().split("\n") if l.strip().startswith("{")]
            return json.loads(lines[-1]) if lines else {"ok": False, "error": "解析失败", "raw": r.stdout[:200], "stderr": r.stderr[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def paired_devices() -> dict:
        """列出已配对的经典蓝牙设备"""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", BluetoothCtl._BT_SCRIPT, "-Mode", "paired"],
                capture_output=True, timeout=15,
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = [l for l in r.stdout.strip().split("\n") if l.strip().startswith("{")]
            return json.loads(lines[-1]) if lines else {"ok": False, "error": "解析失败", "raw": r.stdout[:200], "stderr": r.stderr[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def pair(device_id: str) -> dict:
        """配对蓝牙设备"""
        ps = f'''
[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]

try {{
    $device = [Windows.Devices.Enumeration.DeviceInformation]::CreateFromIdAsync("{device_id}")
    $t = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Enumeration.DeviceInformation]).Invoke($null, @($device))
    $t.Wait(-1)
    $d = $t.Result
    if ($d.Pairing.IsPaired) {{
        ConvertTo-Json @{{ ok=$true; paired="already"; name=$d.Name }}
    }} else {{
        $pairTask = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Enumeration.DevicePairingResult]).Invoke($null, @($d.Pairing.PairAsync()))
        $pairTask.Wait(-1)
        $pr = $pairTask.Result
        ConvertTo-Json @{{ ok=($pr.Status -eq "Paired"); status=$pr.Status.ToString(); name=$d.Name }}
    }}
}} catch {{
    ConvertTo-Json @{{ ok=$false; error=$_.Exception.Message }}
}}
'''
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=20,
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return json.loads(r.stdout.strip().split("\n")[-1])
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def unpair(device_id: str) -> dict:
        """取消配对"""
        ps = f'''
[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]

try {{
    $device = [Windows.Devices.Enumeration.DeviceInformation]::CreateFromIdAsync("{device_id}")
    $t = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Enumeration.DeviceInformation]).Invoke($null, @($device))
    $t.Wait(-1)
    $d = $t.Result
    $unpairTask = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Enumeration.DeviceUnpairingResult]).Invoke($null, @($d.Pairing.UnpairAsync()))
    $unpairTask.Wait(-1)
    $pr = $unpairTask.Result
    ConvertTo-Json @{{ ok=($pr.Status -eq "Unpaired"); status=$pr.Status.ToString() }}
}} catch {{
    ConvertTo-Json @{{ ok=$false; error=$_.Exception.Message }}
}}
'''
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=20,
                text=True, errors="replace",
            )
            return json.loads(r.stdout.strip().split("\n")[-1])
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    # ── 蓝牙音频播放 (A2DP) ──

    @staticmethod
    def connect_audio(device_name_keyword: str = "") -> dict:
        """连接到蓝牙音频设备 (A2DP sink) — 打开 Windows 蓝牙设置面板"""
        try:
            # 打开蓝牙设置面板
            subprocess.Popen(
                ["start", "ms-settings:bluetooth"],
                shell=True,
            )
            time.sleep(1.5)

            # 如果有设备名关键词，尝试找到并连接
            if device_name_keyword:
                # 用键盘导航到设备列表
                import pyautogui
                pyautogui.press("tab", presses=3, interval=0.1)
                time.sleep(0.3)

            return {
                "ok": True,
                "action": "open_bluetooth_settings",
                "hint": "请在蓝牙设置中点击你的手机 → 连接",
                "device_hint": device_name_keyword or "任意设备",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def play_music_to_bluetooth(filepath: str = "", url: str = "") -> dict:
        """播放音乐 (通过默认音频设备)"""
        if filepath and os.path.exists(filepath):
            os.startfile(filepath)
            return {"ok": True, "action": "play", "file": filepath}
        elif url:
            import webbrowser
            webbrowser.open(url)
            return {"ok": True, "action": "open_url", "url": url}
        else:
            # 打开系统音乐文件夹
            music_dir = os.path.join(os.path.expanduser("~"), "Music")
            if os.path.exists(music_dir):
                os.startfile(music_dir)
                return {"ok": True, "action": "open_music_folder", "dir": music_dir}
            return {"ok": False, "error": "无音乐文件路径. 提供 filepath 或 url"}

    @staticmethod
    def set_audio_output(bluetooth_device_name: str = "") -> dict:
        """切换 Windows 音频输出到蓝牙设备"""
        ps = f'''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class AudioSwitcher {{
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string cls, string title);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
}}
"@

# 打开音量混合器 (Win+Ctrl+V)
[AudioSwitcher]::keybd_event(0x5B, 0, 0, [IntPtr]::Zero)  # Win down
[AudioSwitcher]::keybd_event(0x11, 0, 0, [IntPtr]::Zero)  # Ctrl down
[AudioSwitcher]::keybd_event(0x56, 0, 0, [IntPtr]::Zero)  # V down
Start-Sleep -Milliseconds 100
[AudioSwitcher]::keybd_event(0x56, 0, 2, [IntPtr]::Zero)
[AudioSwitcher]::keybd_event(0x11, 0, 2, [IntPtr]::Zero)
[AudioSwitcher]::keybd_event(0x5B, 0, 2, [IntPtr]::Zero)
ConvertTo-Json @{{ ok=$true; action="open_volume_mixer"; hint="请选择蓝牙设备作为播放设备" }}
'''
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=10,
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return json.loads(r.stdout.strip().split("\n")[-1])
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def quick_connect(device_name: str) -> dict:
        """一键连接蓝牙设备流程"""
        results = []

        # Step 1: 打开蓝牙面板
        r1 = BluetoothCtl.connect_audio(device_name)
        results.append({"step": "open_panel", "result": r1})

        # Step 2: 列出已配对设备
        r2 = BluetoothCtl.paired_devices()
        results.append({"step": "list_paired", "count": r2.get("count", 0)})

        # Step 3: 自动连接提示
        found = False
        for d in r2.get("devices", []):
            if device_name.lower() in d.get("name", "").lower():
                found = True
                results.append({"step": "found", "device": d["name"]})
                break

        if found:
            BluetoothCtl.set_audio_output(device_name)
            results.append({"step": "set_audio_output", "done": True})

        return {"ok": True, "steps": results, "device_found": found}

    # ── BLE 扫描 (保留原有) ──

    @staticmethod
    def scan(timeout: float = 5.0) -> dict:
        """扫描附近 BLE 设备"""
        try:
            import asyncio
            from bleak import BleakScanner

            devices = []

            async def _scan():
                async with BleakScanner() as scanner:
                    await asyncio.sleep(timeout)
                for d in scanner.discovered_devices:
                    devices.append({
                        "name": d.name or "Unknown",
                        "address": d.address,
                        "rssi": d.rssi if hasattr(d, 'rssi') else 0,
                    })

            asyncio.run(_scan())
            return {"ok": True, "count": len(devices), "devices": devices}
        except ImportError:
            return {"ok": False, "error": "bleak 未安装"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def connect(address: str) -> dict:
        """连接 BLE 设备"""
        try:
            import asyncio
            from bleak import BleakClient

            async def _connect():
                async with BleakClient(address) as client:
                    services = client.services
                    return {"ok": True, "connected": True, "services_count": len(services)}

            return asyncio.run(_connect())
        except ImportError:
            return {"ok": False, "error": "bleak 未安装"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def windows_bt_dialog() -> dict:
        """打开 Windows 蓝牙设置"""
        try:
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
            return {"ok": True, "action": "open_bt_settings"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}

    @staticmethod
    def full_scan() -> dict:
        """完整扫描: 经典蓝牙 + 已配对 + 当前连接状态"""
        classic = BluetoothCtl.classic_scan()
        paired = BluetoothCtl.paired_devices()

        # 汇总
        all_devices = []
        seen_ids = set()

        if paired.get("ok"):
            for d in paired.get("devices", []):
                all_devices.append({
                    "name": d.get("name", "Unknown"),
                    "id": d.get("id", "")[:40],
                    "type": "paired",
                    "connected": False,  # 需要额外 API 确认
                })
                seen_ids.add(d.get("id", ""))

        if classic.get("ok"):
            for d in classic.get("devices", []):
                if d.get("id", "") not in seen_ids:
                    all_devices.append({
                        "name": d.get("name", "Unknown"),
                        "id": d.get("id", "")[:40],
                        "type": d.get("paired", "unpaired"),
                        "can_pair": d.get("canPair", False),
                    })

        return {"ok": True, "total": len(all_devices), "devices": all_devices}


# ═══════════════════════════════════════════════════════
# 统一设备管理器
# ═══════════════════════════════════════════════════════

class DeviceManager:
    """GBT 设备管理器 — 统一键盘/鼠标/桌面/蓝牙控制"""

    def __init__(self):
        self.keyboard = KeyboardCtl()
        self.mouse = MouseCtl()
        self.desktop = DesktopCtl()
        self.bluetooth = BluetoothCtl()
        self._ready = True

    def ready(self) -> bool:
        return self._ready

    def status(self) -> dict:
        return {
            "keyboard": True,
            "mouse": True,
            "desktop": True,
            "bluetooth": self._ble_available(),
            "display": self._display_info(),
        }

    def _ble_available(self) -> bool:
        try:
            import bleak
            return True
        except ImportError:
            return False

    def _display_info(self) -> dict:
        try:
            import pyautogui
            s = pyautogui.size()
            return {"width": s.width, "height": s.height}
        except Exception:
            return {}

    # ── 操盘场景快捷操作 ──

    def trade_shortcuts(self) -> dict:
        """操盘快捷操作集"""
        return {
            "复制": "ctrl+c",
            "粘贴": "ctrl+v",
            "刷新": "f5",
            "切换窗口": "alt+tab",
            "截图": "win+shift+s",
            "显示桌面": "win+d",
            "运行": "win+r",
            "任务管理器": "ctrl+shift+esc",
        }

    def broker_login_click(self, login_button_pos: tuple = None) -> dict:
        """券商登录按钮点击 (带图像识别降级)"""
        if login_button_pos:
            return self.mouse.click(login_button_pos[0], login_button_pos[1], clicks=1)
        # 尝试常见位置: 屏幕右上角
        size = self.mouse.screen_size()
        if size["ok"]:
            x = int(size["width"] * 0.85)
            y = int(size["height"] * 0.12)
            return self.mouse.click(x, y)
        return {"ok": False, "error": "无法定位登录按钮"}

    def fill_trade_form(self, stock_code: str, price: float, lots: int) -> dict:
        """填充交易表单 (模拟键盘操作)"""
        steps = []
        # 输入股票代码
        self.keyboard.typewrite(stock_code, interval=0.05)
        steps.append(f"输入代码 {stock_code}")
        time.sleep(0.2)
        # Tab 切换到价格
        self.keyboard.press("tab")
        time.sleep(0.1)
        # 输入价格
        self.keyboard.typewrite(f"{price:.2f}", interval=0.05)
        steps.append(f"输入价格 {price:.2f}")
        time.sleep(0.2)
        # Tab 切换到数量
        self.keyboard.press("tab")
        time.sleep(0.1)
        # 输入手数
        self.keyboard.typewrite(str(lots), interval=0.05)
        steps.append(f"输入手数 {lots}")
        return {"ok": True, "steps": steps}

    def fill_trade_form_with_anchors(self, stock_code: str, price: float, lots: int, anchors: dict) -> dict:
        """按 OCR 检出的锚点填充交易表单"""
        steps = []
        required = ("stock_code", "price", "lots")
        missing = [key for key in required if not anchors.get(key)]
        if missing:
            return {"ok": False, "error": "缺少锚点: " + ",".join(missing)}

        fields = [
            ("stock_code", stock_code, "代码"),
            ("price", f"{price:.2f}", "价格"),
            ("lots", str(lots), "手数"),
        ]
        for key, value, label in fields:
            point = anchors.get(key) or {}
            x = int(point.get("x", 0) or 0)
            y = int(point.get("y", 0) or 0)
            if x <= 0 or y <= 0:
                return {"ok": False, "error": f"{label}锚点无效"}
            self.mouse.click(x, y, clicks=1)
            time.sleep(0.15)
            self.keyboard.hotkey("ctrl", "a")
            time.sleep(0.05)
            self.keyboard.typewrite(value, interval=0.03)
            steps.append(f"点击{label}框 ({x},{y})")
            steps.append(f"输入{label} {value}")
            time.sleep(0.15)
        return {"ok": True, "steps": steps, "used_anchors": anchors}

    def emergency_close(self) -> dict:
        """紧急关闭 — Alt+F4"""
        return self.keyboard.hotkey("alt", "f4")


# ── 全局单例 ──
_device_mgr: DeviceManager = None


def get_device() -> DeviceManager:
    global _device_mgr
    if _device_mgr is None:
        _device_mgr = DeviceManager()
    return _device_mgr


L.info("GBT DeviceCtl v1.0 已加载: 键盘 + 鼠标 + 桌面 + 蓝牙")
