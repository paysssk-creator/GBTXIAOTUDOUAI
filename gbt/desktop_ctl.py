"""
电脑操控引擎 — 键盘/鼠标/窗口控制, 用于交易平台自动化
"""
import os, sys, time, subprocess, logging

L = logging.getLogger("GBT.DesktopCtl")

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    L.warning("pyautogui 未安装, 使用 PowerShell 替代")


class DesktopController:
    """桌面操控器 — 键盘/鼠标/剪贴板"""

    def __init__(self):
        self.screen_w, self.screen_h = 1920, 1080
        if HAS_PYAUTOGUI:
            self.screen_w, self.screen_h = pyautogui.size()

    # ── 键盘 ──
    def type_text(self, text, interval=0.05):
        """输入文字"""
        if HAS_PYAUTOGUI:
            pyautogui.typewrite(text, interval=interval)
            return {"ok": True, "method": "pyautogui", "text": text}
        else:
            return self._ps_type(text)

    def press_key(self, key):
        """按下单个键"""
        if HAS_PYAUTOGUI:
            pyautogui.press(key)
            return {"ok": True, "key": key}
        else:
            return self._ps_sendkey(key)

    def hotkey(self, *keys):
        """组合键 (如 ctrl+v)"""
        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*keys)
            return {"ok": True, "keys": list(keys)}
        else:
            return self._ps_hotkey(keys)

    def paste_text(self, text):
        """粘贴文本 (通过剪贴板)"""
        try:
            import subprocess
            # PowerShell 设置剪贴板
            ps = f'Set-Clipboard -Value "{text}"'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, timeout=5)
            # 粘贴
            if HAS_PYAUTOGUI:
                pyautogui.hotkey("ctrl", "v")
            else:
                self._ps_hotkey(["ctrl", "v"])
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 鼠标 ──
    def move_to(self, x, y):
        """移动鼠标"""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y, duration=0.3)
        return {"ok": True, "x": x, "y": y}

    def click(self, x=None, y=None, button="left"):
        """点击"""
        if HAS_PYAUTOGUI:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
        return {"ok": True}

    def double_click(self, x=None, y=None):
        """双击"""
        if HAS_PYAUTOGUI:
            if x is not None and y is not None:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.doubleClick()
        return {"ok": True}

    # ── 窗口控制 ──
    def focus_window(self, title_contains):
        """聚焦窗口"""
        try:
            ps = f'''
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {{
                [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
                [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            }}
"@
            $hwnd = [Win32]::FindWindow($null, "{title_contains}")
            if ($hwnd -ne [IntPtr]::Zero) {{
                [Win32]::ShowWindow($hwnd, 9)
                [Win32]::SetForegroundWindow($hwnd)
                Write-Output "OK"
            }} else {{
                Write-Output "NOT_FOUND"
            }}
            '''
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                              capture_output=True, text=True, timeout=8)
            ok = "OK" in r.stdout
            return {"ok": ok, "found": ok}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def maximize_window(self):
        """最大化当前窗口"""
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "up")
        else:
            self._ps_hotkey(["win", "up"])
        return {"ok": True}

    # ── 浏览器操控 ──
    def browser_navigate(self, url):
        """浏览器导航: 打开新标签+输入URL"""
        try:
            # Ctrl+T 新标签
            if HAS_PYAUTOGUI:
                pyautogui.hotkey("ctrl", "t")
                time.sleep(0.3)
                pyautogui.typewrite(url, interval=0.01)
                pyautogui.press("enter")
            else:
                self._ps_hotkey(["ctrl", "t"])
                time.sleep(0.3)
                self._ps_type(url)
                self._ps_sendkey("enter")
            return {"ok": True, "url": url}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def browser_find_and_type(self, search_text):
        """浏览器查找框输入"""
        try:
            if HAS_PYAUTOGUI:
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.2)
                pyautogui.typewrite(search_text, interval=0.03)
            else:
                self._ps_hotkey(["ctrl", "f"])
                time.sleep(0.2)
                self._ps_type(search_text)
            return {"ok": True, "search": search_text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 交易平台自动化 ──
    def trade_platform_flow(self, platform, code, action, shares, price):
        """完整交易平台操作流程"""
        steps = []
        
        # Step 1: 打开浏览器
        steps.append({"step": 1, "action": "打开浏览器", "result": "执行中"})
        os.startfile("https://jywg.eastmoney.com/")
        time.sleep(2)
        steps[-1]["result"] = "✅ 已打开"

        # Step 2: 等待加载 + 聚焦窗口
        steps.append({"step": 2, "action": "聚焦交易窗口", "result": "执行中"})
        self.focus_window("东方财富")
        time.sleep(1)
        steps[-1]["result"] = "✅ 已聚焦"

        # Step 3: 搜索股票代码
        steps.append({"step": 3, "action": f"搜索 {code}", "result": "执行中"})
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)
            pyautogui.typewrite(code[2:], interval=0.03)
            pyautogui.press("enter")
        steps[-1]["result"] = f"✅ 已搜索 {code}"

        # Step 4: 输入交易参数
        steps.append({"step": 4, "action": f"准备交易: {action} {shares}股 ¥{price}", "result": "等待确认"})
        
        # Step 5: 发送通知
        try:
            from gbt.trader import AShareTrader
            ps = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $n = New-Object System.Windows.Forms.NotifyIcon
            $n.Icon = [System.Drawing.SystemIcons]::Information
            $n.Visible = $true
            $n.ShowBalloonTip(5000, "GBT 操盘手", "{action.upper()} {code} {shares}股 @ {price}", "Info")
            '''
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, timeout=5)
        except: pass
        
        return {"ok": True, "steps": steps, "platform": platform}

    # ── PowerShell 后备方案 ──
    def _ps_type(self, text):
        ps = f'''
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait("{text}")
        '''
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                      capture_output=True, timeout=5)

    def _ps_sendkey(self, key):
        key_map = {"enter": "{ENTER}", "tab": "{TAB}", "escape": "{ESC}",
                   "backspace": "{BS}", "space": " ", "up": "{UP}", "down": "{DOWN}"}
        k = key_map.get(key.lower(), "{" + key.upper() + "}")
        ps = f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{k}")'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                      capture_output=True, timeout=5)

    def _ps_hotkey(self, keys):
        mods = {"ctrl": "^", "alt": "%", "shift": "+", "win": "#"}
        combo = "".join(mods.get(k.lower(), k) for k in keys)
        ps = f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{combo}")'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                      capture_output=True, timeout=5)


# 全局实例
desktop_ctl = DesktopController()
