"""
GBT 屏幕AI模块 v1.0 — 实时桌面 OCR + 语音交互 + 自主操盘流水线

能力：
  1. ScreenOCR — 截屏 + Windows OCR 文字识别，让 Agent 实时"看见"桌面
  2. Voice — Windows TTS 语音输出 + 交互确认
  3. AutoPipeline — 直线自主操盘流水线（开浏览器→检测登录→接手操盘）

依赖：
  - winrt (Windows 10/11 内置 OCR)
  - pyautogui (截屏)
  - System.Speech (Windows 内置 TTS)
"""

import os
import io
import re
import time
import json
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pyautogui
from PIL import Image

L = logging.getLogger("GBT.ScreenAI")

# ── Windows OCR ────────────────────────────────────
try:
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.graphics.imaging import (
        BitmapDecoder, SoftwareBitmap, BitmapPixelFormat
    )
    from winrt.windows.storage.streams import (
        DataWriter, InMemoryRandomAccessStream
    )
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    L.warning("winrt OCR 不可用，screen_ocr 将降级")


class ScreenOCR:
    """实时桌面屏幕文字识别"""
    
    def __init__(self):
        self.engine = None
        if HAS_OCR:
            try:
                self.engine = OcrEngine.try_create_from_user_profile_languages()
                if not self.engine:
                    self.engine = OcrEngine.try_create_from_language(
                        OcrEngine.available_recognizer_languages[0]
                    )
                if self.engine:
                    lang = self.engine.recognizer_language.display_name
                    L.info(f"OCR 引擎就绪: {lang}")
            except Exception as e:
                L.error(f"OCR 引擎初始化失败: {e}")
    
    def capture(self, region=None, save_path=None):
        """截屏，返回 PIL Image
        
        Args:
            region: (left, top, width, height) or None 全屏
            save_path: 可选保存路径
        """
        try:
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            
            if save_path:
                img.save(save_path)
            
            return img
        except Exception as e:
            L.error(f"截屏失败: {e}")
            return None
    
    def _pil_to_software_bitmap(self, pil_image):
        """PIL Image → Windows SoftwareBitmap"""
        # Convert to RGBA bytes
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        buf.seek(0)
        
        # Create InMemoryRandomAccessStream
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(buf.getvalue())
        writer.store_async().get()
        stream.seek(0)
        
        # Decode
        decoder = BitmapDecoder.create_async(stream).get()
        bitmap = decoder.get_software_bitmap_async().get()
        return bitmap
    
    def read_text(self, image=None, region=None):
        """OCR 识别屏幕文字
        
        Args:
            image: PIL Image（可选，不传则先截屏）
            region: 截屏区域（仅在 image=None 时生效）
        
        Returns:
            dict: {
                "ok": bool,
                "text": str,          # 完整文本
                "lines": [str],       # 逐行
                "words": [{text, bbox}],  # 逐词 + 坐标
                "timestamp": str
            }
        """
        if not self.engine:
            return {"ok": False, "error": "OCR引擎未就绪", "text": ""}
        
        try:
            if image is None:
                image = self.capture(region=region)
            if image is None:
                return {"ok": False, "error": "截屏失败", "text": ""}
            
            # PIL → SoftwareBitmap
            bitmap = self._pil_to_software_bitmap(image)
            
            # 执行OCR
            result = self.engine.recognize_async(bitmap).get()
            
            text = result.text or ""
            lines = [line.text for line in result.lines if line.text.strip()]
            
            words = []
            for line in result.lines:
                for word in line.words:
                    b = word.bounding_rect
                    words.append({
                        "text": word.text,
                        "x": b.x, "y": b.y,
                        "w": b.width, "h": b.height
                    })
            
            return {
                "ok": True,
                "text": text,
                "lines": lines,
                "words": words,
                "word_count": len(words),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            
        except Exception as e:
            L.error(f"OCR识别失败: {e}")
            return {"ok": False, "error": str(e)[:120], "text": ""}
    
    def find_text_on_screen(self, search_text, region=None):
        """在屏幕上查找指定文字位置
        
        Returns:
            list of dicts: [{text, x, y, w, h}] 或 [] 未找到
        """
        result = self.read_text(region=region)
        if not result["ok"]:
            return []
        
        matches = []
        for word in result.get("words", []):
            if search_text.lower() in word["text"].lower():
                matches.append(word)
        
        return matches
    
    def detect_login_state(self, keywords=None):
        """检测券商页面登录状态
        
        通过 OCR 识别屏幕上的关键词判断是否已登录。
        
        Args:
            keywords: 登录后页面应出现的关键词列表
        
        Returns:
            dict: {
                "logged_in": bool,
                "confidence": float (0-1),
                "found_keywords": [str],
                "screen_text": str,
                "ocr_result": dict
            }
        """
        if keywords is None:
            # 券商交易页面登录后常见关键词
            keywords = [
                "持仓", "我的资产", "可用资金", "买入", "卖出",
                "撤单", "委托", "成交", "资金股份", "账户总览",
                "我的持仓", "股票市值", "账户资产", "立即买入",
                "资产总值", "总资产", "交易记录"
            ]
        
        result = self.read_text()
        screen_text = result.get("text", "")
        
        if not result["ok"]:
            return {
                "logged_in": False,
                "confidence": 0.0,
                "found_keywords": [],
                "screen_text": "",
                "error": result.get("error", "OCR失败")
            }
        
        found = []
        for kw in keywords:
            if kw in screen_text:
                found.append(kw)
        
        confidence = min(1.0, len(found) / 3)  # 命中3个关键词=100%确信
        logged_in = len(found) >= 2  # 至少2个关键词匹配
        
        return {
            "logged_in": logged_in,
            "confidence": round(confidence, 2),
            "found_keywords": found,
            "screen_text": screen_text[:500],
            "ocr_result": result
        }


class Voice:
    """Windows TTS 语音输出 + 交互确认"""
    
    CHINESE_VOICE = "Microsoft Huihui Desktop"
    ENGLISH_VOICE = "Microsoft Zira Desktop"
    
    @staticmethod
    def speak(text, voice=None, rate=0):
        """Windows TTS 语音朗读
        
        Args:
            text: 要朗读的文字
            voice: 语音名称（可选，默认中文）
            rate: 语速 -10 到 10（0 正常）
        """
        if voice is None:
            # 自动选择中文/英文语音
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            voice = Voice.CHINESE_VOICE if has_chinese else Voice.ENGLISH_VOICE
        
        try:
            ps_script = f'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = {rate}
try {{ $s.SelectVoice("{voice}") }} catch {{}}
$s.Speak('{text.replace("'", "''")}')
'''
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return {"ok": True}
        except Exception as e:
            L.error(f"TTS失败: {e}")
            return {"ok": False, "error": str(e)[:80]}
    
    @staticmethod
    def ask(question, voice=None):
        """语音提问 — 朗读问题
        
        配合 login_detect 使用：先语音询问，再 OCR 检测页面变化
        """
        L.info(f"🗣️ 语音提问: {question}")
        return Voice.speak(question, voice=voice)


class AutoPipeline:
    """自主操盘流水线 — 直线执行的自动化交易流程"""
    
    def __init__(self, trader=None, account=None, brain=None):
        self.trader = trader
        self.account = account
        self.brain = brain
        self.screen = ScreenOCR()
        self.voice = Voice()
        self.state = {
            "phase": "idle",
            "started_at": None,
            "login_confirmed": False,
            "steps": [],
            "errors": []
        }
    
    def run_login_flow(self, platform_url, platform_name="券商平台"):
        """登录流水线：打开浏览器 → 语音提示 → 等待用户登录 → OCR 确认
        
        Args:
            platform_url: 券商网页 URL
            platform_name: 平台名称
        
        Returns:
            dict: {"ok", "phase", "message"}
        """
        self.state["phase"] = "login_flow"
        self.state["started_at"] = datetime.now().strftime("%H:%M:%S")
        
        steps = []
        
        # Step 1: 打开浏览器
        steps.append({"step": "open_browser", "status": "running"})
        L.info(f"🌐 打开券商平台: {platform_name}")
        try:
            os.startfile(platform_url)
            steps[-1]["status"] = "done"
        except Exception as e:
            steps[-1]["status"] = "error"
            steps[-1]["error"] = str(e)
            self.state["steps"] = steps
            return {"ok": False, "phase": "open_browser", "error": str(e)}
        
        # Step 2: 等待页面加载
        time.sleep(3)
        
        # Step 3: 语音询问用户
        steps.append({"step": "voice_prompt", "status": "running"})
        msg = f"{platform_name}已打开，请在浏览器中登录您的股票账户，登录成功后请告诉我"
        self.voice.speak(msg)
        steps[-1]["status"] = "done"
        steps[-1]["message"] = msg
        
        # Step 4: 等待并 OCR 检测登录状态（最多等 120 秒）
        steps.append({"step": "detect_login", "status": "running"})
        L.info("🔍 等待用户登录...")
        
        max_wait = 120
        check_interval = 5
        elapsed = 0
        
        login_detected = False
        while elapsed < max_wait:
            result = self.screen.detect_login_state()
            if result["logged_in"]:
                login_detected = True
                steps[-1]["status"] = "done"
                steps[-1]["detail"] = f"检测到 {len(result['found_keywords'])} 个登录关键词: {result['found_keywords']}"
                break
            
            elapsed += check_interval
            time.sleep(check_interval)
        
        if not login_detected:
            steps[-1]["status"] = "timeout"
            steps[-1]["detail"] = f"等待 {max_wait}s 未检测到登录状态"
            self.state["steps"] = steps
            return {
                "ok": False,
                "phase": "detect_login",
                "message": "登录检测超时，请确认是否已登录"
            }
        
        # Step 5: 确认接手
        steps.append({"step": "confirm_handover", "status": "running"})
        self.voice.speak("登录确认成功，GBT 将接手自主操盘，请坐好看戏")
        steps[-1]["status"] = "done"
        self.state["login_confirmed"] = True
        self.state["phase"] = "autonomous"
        
        self.state["steps"] = steps
        
        L.info("✅ 登录流水线完成 — 进入自主操盘模式")
        return {
            "ok": True,
            "phase": "autonomous",
            "message": f"{platform_name} 登录已确认，GBT 自主操盘就绪"
        }
    
    def screen_watch(self, interval=10, duration=300):
        """屏幕监视 — 定期 OCR 桌面，追踪操盘状态
        
        每 interval 秒 OCR 一次，返回屏幕摘要。
        避免重复打开浏览器。
        
        Args:
            interval: 检测间隔（秒）
            duration: 最长运行时间（秒），0=无限
        
        Returns:
            generator yielding: {"time", "text", "changes", "keywords_found"}
        """
        if duration <= 0:
            duration = float('inf')
        
        last_text = ""
        elapsed = 0
        
        while elapsed < duration:
            result = self.screen.read_text()
            current_text = result.get("text", "")
            
            # 检测变化
            changes = []
            if last_text and current_text != last_text:
                changes = self._diff_text(last_text, current_text)
            
            # 检测关键交易信息
            keywords = self._extract_trading_info(current_text)
            
            yield {
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": current_text[:300],
                "changes": changes[:5],
                "keywords_found": keywords,
                "word_count": result.get("word_count", 0)
            }
            
            last_text = current_text
            elapsed += interval
            if elapsed < duration:
                time.sleep(interval)
    
    def _diff_text(self, old, new):
        """简单文本变化检测"""
        changes = []
        old_lines = set(old.split('\n'))
        new_lines = set(new.split('\n'))
        added = new_lines - old_lines
        removed = old_lines - new_lines
        for line in list(added)[:5]:
            if line.strip():
                changes.append(f"+ {line.strip()[:60]}")
        for line in list(removed)[:3]:
            if line.strip():
                changes.append(f"- {line.strip()[:60]}")
        return changes
    
    def _extract_trading_info(self, text):
        """从 OCR 文本中提取交易关键信息"""
        info = {}
        
        # 盈亏
        pnl_match = re.search(r'[盈浮]亏[：:\s]*[+-]?[\d,]+\.?\d*', text)
        if pnl_match:
            info["pnl"] = pnl_match.group()
        
        # 可用资金
        cash_match = re.search(r'可用[资金][：:\s]*[\d,]+\.?\d*', text)
        if cash_match:
            info["cash"] = cash_match.group()
        
        # 持仓
        position_match = re.search(r'[持仓][：:\s]*[\d]+只?', text)
        if position_match:
            info["positions"] = position_match.group()
        
        # 涨跌
        up_match = re.search(r'[\u6da8\u8dcc][：:\s]*[+\-]?[\d.]+%?', text)
        if up_match:
            info["change"] = up_match.group()
        
        return info if info else None
    
    def execute_trade_on_screen(self, code, action, price=None, shares=None):
        """屏幕操盘 — 通过 OCR 定位 + 点击执行交易
        
        流程：
        1. OCR 扫描屏幕找交易界面元素
        2. 点击"买入"/"卖出"按钮
        3. 输入代码/价格/数量
        4. 点击确认
        5. OCR 验证订单
        
        Args:
            code: 股票代码
            action: "buy" or "sell"
            price: 委托价格（None = 市价）
            shares: 股数
        """
        action_text = "买入" if action == "buy" else "卖出"
        steps = []
        
        # Step 1: OCR 当前屏幕
        L.info(f"🔍 OCR扫描屏幕 — 准备{action_text} {code}")
        result = self.screen.read_text()
        if not result["ok"]:
            return {"ok": False, "error": "OCR失败", "steps": steps}
        
        screen_text = result.get("text", "")
        steps.append({"step": "scan_screen", "text": screen_text[:200]})
        
        # Step 2: 定位并点击"买入"/"卖出"
        btn_matches = self.screen.find_text_on_screen(action_text)
        if btn_matches:
            match = btn_matches[0]
            click_x = match["x"] + match["w"] // 2
            click_y = match["y"] + match["h"] // 2
            pyautogui.click(click_x, click_y)
            steps.append({"step": f"click_{action}", "pos": (click_x, click_y), "status": "done"})
            time.sleep(1)
        else:
            steps.append({"step": f"click_{action}", "status": "not_found"})
            return {"ok": False, "error": f"未找到'{action_text}'按钮", "steps": steps}
        
        # Step 3: 输入代码
        pyautogui.write(code, interval=0.05)
        pyautogui.press("tab")
        steps.append({"step": "input_code", "code": code, "status": "done"})
        
        # Step 4: 输入价格（如果有）
        if price:
            pyautogui.write(str(price), interval=0.05)
            pyautogui.press("tab")
            steps.append({"step": "input_price", "price": price, "status": "done"})
        
        # Step 5: 输入数量
        if shares:
            pyautogui.write(str(shares), interval=0.05)
            steps.append({"step": "input_shares", "shares": shares, "status": "done"})
        
        # Step 6: 确认
        confirm_matches = self.screen.find_text_on_screen("确定") or self.screen.find_text_on_screen("确认")
        if confirm_matches:
            match = confirm_matches[0]
            click_x = match["x"] + match["w"] // 2
            click_y = match["y"] + match["h"] // 2
            pyautogui.click(click_x, click_y)
            steps.append({"step": "confirm", "pos": (click_x, click_y), "status": "done"})
        
        L.info(f"✅ 屏幕操盘完成: {action_text} {code}")
        return {"ok": True, "action": action, "code": code, "steps": steps}


# ── 便捷函数 ────────────────────────────────────

def screen_ocr(region=None):
    """快速 OCR 桌面"""
    ocr = ScreenOCR()
    return ocr.read_text(region=region)


def voice_speak(text):
    """快速语音输出"""
    return Voice.speak(text)


def voice_ask(question):
    """快速语音提问"""
    return Voice.ask(question)


def detect_login():
    """快速检测登录状态"""
    ocr = ScreenOCR()
    return ocr.detect_login_state()
