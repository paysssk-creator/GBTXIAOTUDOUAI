# -*- coding: utf-8 -*-
"""
gbt/audio_ctrl.py — GBT 音频设备控制引擎 v1.0

使用 pycaw 枚举设备 + IPolicyConfig COM 切换默认端点
"""
import sys, subprocess, json, time, logging
from ctypes import byref, cast, POINTER
from comtypes import GUID, CLSCTX_ALL

L = logging.getLogger("GBT.AudioCtrl")

# IPolicyConfig CLSID + IID for SetDefaultEndpoint
CLSID_PolicyConfig = "{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}"
IID_IPolicyConfig = "{F8679F50-850A-41CF-9C72-430F290290C8}"


class AudioController:
    """Windows 音频设备控制器 (pycaw + IPolicyConfig)"""

    def __init__(self):
        self._last_devices: list = []
        self._bluetooth_device_id: str = ""

    def list_devices(self) -> dict:
        """列出所有活跃的播放设备 (通过 pycaw)"""
        try:
            from pycaw.pycaw import AudioUtilities

            devices = AudioUtilities.GetAllDevices()
            default = AudioUtilities.GetSpeakers()
            default_id = str(default.id) if hasattr(default, 'id') else ""

            dev_list = []
            for d in devices:
                name = d.FriendlyName
                did = str(d.id)
                try:
                    state_val = d.state.value
                except AttributeError:
                    state_val = -1
                is_default = (did == default_id)
                dev_list.append({
                        "name": str(name),
                        "id": str(did),
                        "state": state_val,
                        "isDefault": is_default,
                })

            self._last_devices = dev_list
            return {
                "ok": True,
                "default": str(default.FriendlyName),
                "devices": dev_list,
                "count": len(dev_list),
            }
        except ImportError:
            return {"ok": False, "error": "pycaw 未安装. pip install pycaw"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:120]}

    def find_bluetooth(self) -> dict:
        """查找蓝牙音频设备"""
        info = self.list_devices()
        if not info["ok"]:
            return info

        bt_devices = []
        for d in info.get("devices", []):
            name = d.get("name", "").lower()
            if any(k in name for k in ["iphone", "bluetooth", "hand", "headset", "headphone", "bt", "ear", "airpod"]):
                bt_devices.append(d)

        if bt_devices:
            self._bluetooth_device_id = bt_devices[0]["id"]
            L.info(f"蓝牙音频设备: {bt_devices[0]['name']}")
            return {"ok": True, "found": True, "device": bt_devices[0], "all": bt_devices}
        return {"ok": True, "found": False, "all_devices": info.get("devices", [])}

    def switch_to(self, device_id: str) -> dict:
        """切换默认音频输出到指定设备 (IPolicyConfig COM)"""
        try:
            from comtypes.client import CreateObject
            pc = CreateObject(CLSID_PolicyConfig, interface=IID_IPolicyConfig, clsctx=CLSCTX_ALL)
            # eConsole=0, eMultimedia=1, eCommunications=2
            pc.SetDefaultEndpoint(device_id, 0)
            pc.SetDefaultEndpoint(device_id, 1)
            pc.SetDefaultEndpoint(device_id, 2)
            L.info(f"已切换到: {device_id[:60]}...")
            return {"ok": True, "device_id": device_id}
        except Exception as e:
            return {"ok": False, "error": str(e)[:120], "hint": "可能需要管理员权限"}

    def switch_to_bluetooth(self) -> dict:
        """自动查找并切换到蓝牙音频设备"""
        bt = self.find_bluetooth()
        if not bt.get("found"):
            return {"ok": False, "error": "未找到蓝牙音频设备. 请先在蓝牙设置中点击iPhone的连接按钮"}
        return self.switch_to(bt["device"]["id"])

    def switch_to_speakers(self) -> dict:
        """切换回笔记本扬声器"""
        info = self.list_devices()
        if not info["ok"]:
            return info
        for d in info.get("devices", []):
            name = d.get("name", "").lower()
            if "speaker" in name or "realtek" in name:
                return self.switch_to(d["id"])
        return {"ok": False, "error": "未找到扬声器"}

    def get_default(self) -> dict:
        """获取当前默认播放设备"""
        info = self.list_devices()
        if not info["ok"]:
            return info
        for d in info.get("devices", []):
            if d.get("isDefault"):
                return {"ok": True, "device": d}
        return {"ok": False, "error": "无默认设备"}

    def wait_for_bluetooth(self, timeout: float = 30.0, interval: float = 2.0) -> dict:
        """轮询等待蓝牙音频设备出现"""
        start = time.time()
        while time.time() - start < timeout:
            bt = self.find_bluetooth()
            if bt.get("found"):
                return bt
            time.sleep(interval)
        return {"ok": False, "error": f"等待{timeout}s后未检测到蓝牙设备"}

    def auto_connect_and_switch(self) -> dict:
        """一键: 检测→切换→确认"""
        bt = self.wait_for_bluetooth(timeout=5.0, interval=1.0)
        if bt.get("found"):
            sw = self.switch_to(bt["device"]["id"])
            if sw["ok"]:
                return {"ok": True, "message": f"已切换到: {bt['device']['name']}"}
            return sw
        return {
            "ok": False,
            "error": "蓝牙音频设备未连接",
            "help": "打开蓝牙设置 → iPhone → 连接 → 确保显示'已连接语音、音乐'",
        }


_ctrl = None

def get_audio_ctrl() -> AudioController:
    global _ctrl
    if _ctrl is None:
        _ctrl = AudioController()
    return _ctrl
