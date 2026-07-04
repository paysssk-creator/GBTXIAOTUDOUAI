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

    @staticmethod
    def _center_of(word):
        return {
            "x": int(word["x"] + word["w"] / 2),
            "y": int(word["y"] + word["h"] / 2),
        }

    @staticmethod
    def _input_anchor_from_label(word):
        # 多数券商交易软件在标签右侧放输入框，做一个保守偏移估计
        return {
            "x": int(word["x"] + max(word["w"] + 90, 120)),
            "y": int(word["y"] + max(word["h"] / 2, 12)),
        }

    @staticmethod
    def _sanitize_line(text):
        text = re.sub(r'\s+', ' ', str(text or '')).strip()
        return text[:80]

    @staticmethod
    def _code_hits(text):
        hits = []
        for item in re.findall(r'(?<!\d)(?:60\d{4}|68\d{4}|30\d{4}|00\d{4})(?!\d)', text or ""):
            if item not in hits:
                hits.append(item)
            if len(hits) >= 8:
                break
        return hits

    @staticmethod
    def _extract_money_lines(lines):
        out = []
        for line in lines or []:
            if re.search(r'(可用|资产|盈亏|市值|成本|成交|委托)', line) and re.search(r'[\d,]+(?:\.\d+)?', line):
                clean = ScreenOCR._sanitize_line(line)
                if clean and clean not in out:
                    out.append(clean)
            if len(out) >= 6:
                break
        return out

    @staticmethod
    def _panel_field_keywords(panel):
        if panel == "entrust":
            return [
                "证券代码", "股票代码", "代码", "证券名称", "名称", "委托价格", "委托价",
                "价格", "委托数量", "数量", "股数", "状态", "买入", "卖出", "撤单",
                "申报", "合同编号", "成交数量",
            ]
        return [
            "证券代码", "股票代码", "代码", "证券名称", "名称", "持仓", "持股",
            "股份余额", "股票余额", "可用股份", "可卖数量", "可用余额", "成本价",
            "市价", "最新价", "市值", "参考市值", "参考盈亏", "盈亏",
        ]

    @classmethod
    def _is_panel_header(cls, panel, text):
        clean = cls._sanitize_line(text)
        if not clean:
            return False
        keyword_hits = sum(1 for word in cls._panel_field_keywords(panel) if word in clean)
        number_hits = cls._number_hits(clean)
        if cls._code_hits(clean):
            return False
        if keyword_hits >= 3:
            return True
        if keyword_hits >= 2 and len(number_hits) <= 1 and not cls._detect_action(clean) and not cls._detect_status(clean):
            return True
        return False

    @classmethod
    def _looks_like_panel_row(cls, panel, text):
        clean = cls._sanitize_line(text)
        if not clean or cls._is_panel_header(panel, clean):
            return False
        code_hits = cls._code_hits(clean)
        number_hits = cls._number_hits(clean)
        if panel == "entrust":
            if code_hits and (len(number_hits) >= 2 or cls._detect_action(clean) or cls._detect_status(clean)):
                return True
            if len(number_hits) >= 3 and (cls._detect_action(clean) or cls._detect_status(clean)):
                return True
            return False
        position_keywords = ("持仓", "股份", "余额", "可卖", "可用", "市值", "盈亏", "成本")
        if code_hits and len(number_hits) >= 2:
            return True
        if len(number_hits) >= 4 and any(word in clean for word in position_keywords):
            return True
        return False

    @classmethod
    def _group_words_into_rows(cls, words, bounds=None):
        filtered = []
        bounds = bounds or {}
        left = int(bounds.get("x", 0) or 0)
        top = int(bounds.get("y", 0) or 0)
        right = left + int(bounds.get("w", 0) or 0)
        bottom = top + int(bounds.get("h", 0) or 0)
        for word in words or []:
            text = str(word.get("text", "")).strip()
            if not text:
                continue
            cx = int(word.get("x", 0) + word.get("w", 0) / 2)
            cy = int(word.get("y", 0) + word.get("h", 0) / 2)
            if bounds:
                if cx < left or cx > right or cy < top or cy > bottom:
                    continue
            filtered.append({
                "text": text,
                "x": int(word.get("x", 0) or 0),
                "h": int(word.get("h", 0) or 0),
                "cy": cy,
            })
        filtered.sort(key=lambda item: (item["cy"], item["x"]))
        rows = []
        for word in filtered:
            if not rows:
                rows.append({"cy": word["cy"], "h": max(10, word["h"]), "words": [word]})
                continue
            current = rows[-1]
            tolerance = max(12, int(max(current["h"], word["h"]) * 0.7))
            if abs(word["cy"] - current["cy"]) <= tolerance:
                current["words"].append(word)
                count = len(current["words"])
                current["cy"] = int(((current["cy"] * (count - 1)) + word["cy"]) / count)
                current["h"] = max(current["h"], word["h"])
            else:
                rows.append({"cy": word["cy"], "h": max(10, word["h"]), "words": [word]})
        lines = []
        for row in rows:
            text = " ".join(item["text"] for item in sorted(row["words"], key=lambda item: item["x"]))
            clean = cls._sanitize_line(text)
            if clean and clean not in lines:
                lines.append(clean)
        return lines

    @classmethod
    def _panel_candidate_lines(cls, panel, lines, words, bounds=None):
        candidates = []
        for source in (cls._group_words_into_rows(words, bounds=bounds), lines or []):
            for line in source:
                clean = cls._sanitize_line(line)
                if not clean or clean in candidates:
                    continue
                if cls._is_panel_header(panel, clean):
                    candidates.append(clean)
                    continue
                if cls._looks_like_panel_row(panel, clean) or any(word in clean for word in cls._panel_field_keywords(panel)):
                    candidates.append(clean)
                    continue
                if bounds and re.search(r'[\d,]+(?:\.\d+)?', clean):
                    candidates.append(clean)
            if len(candidates) >= 20:
                break
        return candidates[:20]

    @staticmethod
    def _number_hits(text):
        hits = []
        for item in re.findall(r'(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\d)', text or ""):
            item = item.strip()
            hits.append(item)
            if len(hits) >= 12:
                break
        return hits

    @staticmethod
    def _detect_action(text):
        text = str(text or "")
        for word in ("买入", "卖出", "撤单", "申报"):
            if word in text:
                return word
        return ""

    @staticmethod
    def _detect_status(text):
        text = str(text or "")
        for word in ("已成", "部成", "未成", "已报", "已撤", "废单", "撤单", "申报", "成功", "失败"):
            if word in text:
                return word
        return ""

    @classmethod
    def _build_panel_rows(cls, panel, lines, stock_code=""):
        rows = []
        stock_code = str(stock_code or "").strip()
        for line in lines or []:
            clean = cls._sanitize_line(line)
            if not clean:
                continue
            if cls._is_panel_header(panel, clean) or not cls._looks_like_panel_row(panel, clean):
                continue
            codes = cls._code_hits(clean)
            numbers = cls._number_hits(clean)
            row = {
                "raw": clean,
                "code": codes[0] if codes else "",
                "action": cls._detect_action(clean) if panel == "entrust" else "",
                "status": cls._detect_status(clean) if panel == "entrust" else "",
                "price": "",
                "quantity": "",
                "amount": "",
                "available": "",
                "market_value": "",
                "profit": "",
            }
            numeric_values = [n for n in numbers if n != row["code"]]
            if panel == "entrust":
                if numeric_values:
                    row["price"] = numeric_values[0]
                if len(numeric_values) >= 2:
                    row["quantity"] = numeric_values[1]
                if len(numeric_values) >= 3:
                    row["amount"] = numeric_values[2]
            else:
                if numeric_values:
                    row["quantity"] = numeric_values[0]
                if len(numeric_values) >= 2:
                    row["available"] = numeric_values[1]
                if len(numeric_values) >= 3:
                    row["price"] = numeric_values[2]
                if len(numeric_values) >= 4:
                    row["market_value"] = numeric_values[3]
                if len(numeric_values) >= 5:
                    row["profit"] = numeric_values[4]
            if stock_code and row["code"] and stock_code not in row["code"] and stock_code[-4:] not in row["code"]:
                if stock_code not in clean and stock_code[-4:] not in clean:
                    continue
            if not row["code"] and not any(row[k] for k in ("price", "quantity", "status", "available", "market_value", "profit")):
                continue
            rows.append(row)
            if len(rows) >= 6:
                break
        return rows

    @classmethod
    def _panel_summary(cls, panel, rows):
        if not rows:
            return {}
        summary = {"row_count": len(rows)}
        codes = [row.get("code") for row in rows if row.get("code")]
        if codes:
            summary["codes"] = list(dict.fromkeys(codes))[:6]
        statuses = [row.get("status") for row in rows if row.get("status")]
        if statuses:
            summary["statuses"] = list(dict.fromkeys(statuses))[:6]
        actions = [row.get("action") for row in rows if row.get("action")]
        if actions:
            summary["actions"] = list(dict.fromkeys(actions))[:6]
        if panel == "position":
            profits = [row.get("profit") for row in rows if row.get("profit")]
            if profits:
                summary["profit_samples"] = profits[:4]
        return summary

    @staticmethod
    def _broker_profile(broker=""):
        try:
            from gbt.stock_gate import get_broker_ui_profile
            return get_broker_ui_profile(broker or "东方财富")
        except Exception:
            return {}

    def _panel_bounds_from_keywords(self, words, keywords):
        hits = []
        for word in words or []:
            text = str(word.get("text", "")).strip()
            if any(key in text for key in keywords):
                hits.append(word)
        if not hits:
            return None
        left = min(int(item["x"]) for item in hits)
        top = min(int(item["y"]) for item in hits)
        right = max(int(item["x"] + item["w"]) for item in hits)
        bottom = max(int(item["y"] + item["h"]) for item in hits)
        return {
            "x": max(0, left - 40),
            "y": max(0, top - 30),
            "w": max(120, right - left + 260),
            "h": max(80, bottom - top + 220),
        }

    def detect_trade_panel_readback(self, panel="entrust", stock_code="", broker=""):
        """检测委托/持仓区域回读摘要"""
        result = self.read_text()
        if not result.get("ok"):
            return {
                "ok": False,
                "found": False,
                "panel": panel,
                "codes": [],
                "matched_lines": [],
                "metrics": [],
                "error": result.get("error", "OCR失败"),
            }

        panel = (panel or "entrust").strip().lower()
        if panel not in {"entrust", "position"}:
            panel = "entrust"
        panel_keywords = {
            "entrust": ["委托", "今日委托", "当前委托", "当日委托", "委托查询", "申报", "撤单"],
            "position": ["持仓", "我的持仓", "持仓查询", "资金股份", "股票市值", "可用股份", "持股"],
        }
        profile = self._broker_profile(broker)
        custom_panel_keywords = ((profile.get("panel_keywords") or {}).get(panel) or [])
        if custom_panel_keywords:
            panel_keywords[panel] = list(dict.fromkeys(list(custom_panel_keywords) + panel_keywords[panel]))
        words = result.get("words", [])
        lines = result.get("lines", [])
        bounds = self._panel_bounds_from_keywords(words, panel_keywords[panel])
        candidates = self._panel_candidate_lines(panel=panel, lines=lines, words=words, bounds=bounds)
        selected_lines = []
        for line in candidates:
            if any(key in line for key in panel_keywords[panel]) or self._looks_like_panel_row(panel, line):
                if line not in selected_lines:
                    selected_lines.append(line)
            if len(selected_lines) >= 8:
                break
        if not selected_lines:
            selected_lines = [line for line in candidates if self._looks_like_panel_row(panel, line)][:8]

        text = result.get("text", "")
        codes = self._code_hits("\n".join(selected_lines) if selected_lines else text)
        if stock_code:
            stock_code = str(stock_code).strip()
            focused = []
            for line in selected_lines:
                if stock_code in line or stock_code[-4:] in line:
                    focused.append(line)
            if focused:
                selected_lines = focused + [line for line in selected_lines if line not in focused]
        rows = self._build_panel_rows(panel=panel, lines=selected_lines[:8], stock_code=stock_code)
        metrics = self._extract_money_lines(selected_lines or lines)
        has_panel_keyword = any(key in text for key in panel_keywords[panel]) or any(
            any(key in line for key in panel_keywords[panel]) for line in selected_lines
        )
        has_structured_rows = any(
            sum(1 for key in ("code", "price", "quantity", "available", "status", "market_value", "profit", "amount") if row.get(key)) >= 2
            for row in rows
        )
        credible = bool(bounds or has_panel_keyword or (has_structured_rows and len(selected_lines) >= 2) or (has_structured_rows and metrics))
        rejected_noise = bool((selected_lines or rows or codes) and not credible)
        if not credible:
            codes = []
            selected_lines = []
            metrics = []
            rows = []
        return {
            "ok": True,
            "found": credible,
            "panel": panel,
            "broker": profile.get("name") or broker or None,
            "bounds": bounds,
            "codes": codes,
            "matched_lines": selected_lines[:6],
            "metrics": metrics,
            "rows": rows,
            "summary": self._panel_summary(panel, rows),
            "rejected_noise": rejected_noise,
        }

    def detect_trade_form_anchors(self, action=None, broker=""):
        """检测交易表单锚点

        Returns:
            dict: {
                "ok": bool,
                "found": bool,
                "anchors": {...},
                "keywords": {...},
                "screen_text": str
            }
        }
        """
        result = self.read_text()
        if not result.get("ok"):
            return {
                "ok": False,
                "found": False,
                "anchors": {},
                "keywords": {},
                "screen_text": "",
                "error": result.get("error", "OCR失败"),
            }

        words = result.get("words", [])
        anchor_keywords = {
            "stock_code": ["证券代码", "股票代码", "代码", "证券"],
            "price": ["委托价格", "买入价格", "卖出价格", "价格", "委托价"],
            "lots": ["委托数量", "买入数量", "卖出数量", "数量", "股数"],
            "buy_btn": ["买入", "立即买入"],
            "sell_btn": ["卖出", "立即卖出"],
            "confirm_btn": ["确认", "确定", "提交", "下单", "委托"],
        }
        profile = self._broker_profile(broker)
        custom_anchor_keywords = profile.get("anchor_keywords") or {}
        for key, patterns in custom_anchor_keywords.items():
            merged = list(dict.fromkeys(list(patterns or []) + list(anchor_keywords.get(key, []))))
            anchor_keywords[key] = merged
        if action == "buy":
            anchor_keywords["action_btn"] = ["买入", "立即买入"]
        elif action == "sell":
            anchor_keywords["action_btn"] = ["卖出", "立即卖出"]

        hits = {key: [] for key in anchor_keywords}
        for word in words:
            text = str(word.get("text", "")).strip()
            if not text:
                continue
            for key, patterns in anchor_keywords.items():
                if any(pattern in text for pattern in patterns):
                    hits[key].append(word)

        anchors = {}
        if hits["stock_code"]:
            anchors["stock_code"] = self._input_anchor_from_label(hits["stock_code"][0])
        if hits["price"]:
            anchors["price"] = self._input_anchor_from_label(hits["price"][0])
        if hits["lots"]:
            anchors["lots"] = self._input_anchor_from_label(hits["lots"][0])
        if hits["buy_btn"]:
            anchors["buy_btn"] = self._center_of(hits["buy_btn"][0])
        if hits["sell_btn"]:
            anchors["sell_btn"] = self._center_of(hits["sell_btn"][0])
        if hits["confirm_btn"]:
            anchors["confirm_btn"] = self._center_of(hits["confirm_btn"][0])
        if hits.get("action_btn"):
            anchors["action_btn"] = self._center_of(hits["action_btn"][0])

        found = len(anchors) > 0
        return {
            "ok": True,
            "found": found,
            "broker": profile.get("name") or broker or None,
            "anchors": anchors,
            "keywords": {key: [item.get("text", "") for item in values[:5]] for key, values in hits.items()},
            "screen_text": (result.get("text") or "")[:500],
            "ocr_result": result,
        }

    def detect_trade_confirm_dialog(self, action=None, stock_code="", broker=""):
        """检测交易确认弹窗与提交按钮"""
        result = self.read_text()
        if not result.get("ok"):
            return {
                "ok": False,
                "found": False,
                "confirm_btn": None,
                "keywords": [],
                "error": result.get("error", "OCR失败"),
            }

        action = (action or "").strip().lower()
        action_words = []
        if action == "buy":
            action_words = ["买入", "立即买入"]
        elif action == "sell":
            action_words = ["卖出", "立即卖出"]

        dialog_keywords = [
            "委托确认", "请确认", "确认下单", "下单确认",
            "确认委托", "买入确认", "卖出确认", "委托提交",
        ] + action_words
        confirm_keywords = ["确认", "确定", "提交", "委托", "下单"]
        profile = self._broker_profile(broker)
        custom_confirm = ((profile.get("anchor_keywords") or {}).get("confirm_btn") or [])
        if custom_confirm:
            confirm_keywords = list(dict.fromkeys(list(custom_confirm) + confirm_keywords))
        if stock_code:
            dialog_keywords.append(str(stock_code)[-4:])

        found_dialog = []
        confirm_btn = None
        for word in result.get("words", []):
            text = str(word.get("text", "")).strip()
            if not text:
                continue
            if any(key in text for key in dialog_keywords):
                found_dialog.append(text)
            if confirm_btn is None and any(key in text for key in confirm_keywords):
                confirm_btn = self._center_of(word)

        return {
            "ok": True,
            "found": bool(found_dialog or confirm_btn),
            "broker": profile.get("name") or broker or None,
            "confirm_btn": confirm_btn,
            "keywords": found_dialog[:8],
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
            import base64 as _b64
            safe_text = _b64.b64encode(text.encode('utf-8')).decode('ascii')
            ps_script = f'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = {rate}
try {{ $s.SelectVoice("{voice}") }} catch {{}}
$s.Speak([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("{safe_text}")))
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
    
    def monitor_trade_screen(self, code, action, expected_text=None, timeout=60, broker=""):
        """监视交易屏幕 — OCR 验证交易执行结果
        
        在交易提交后，定期 OCR 扫描屏幕，检测：
        1. 订单确认弹窗
        2. 成交结果
        3. 持仓变化
        
        Args:
            code: 股票代码
            action: 'buy'/'sell'
            expected_text: 期望在屏幕上看到的文字（如"委托已提交"）
            timeout: 最长等待时间（秒）
        
        Returns:
            dict: {"ok", "found", "screen_text", "elapsed"}
        """
        action_cn = "买入" if action == "buy" else "卖出"
        L.info(f"👁 开始监视屏幕 — {action_cn} {code}")
        
        keywords = [
            "委托已提交", "委托成功", "已申报", "已成", "部分成",
            "已成交", "委托失败", "废单", "撤单",
            action_cn, code[-4:]  # 后4位代码
        ]
        profile = self._broker_profile(broker)
        panel_keywords = profile.get("panel_keywords") or {}
        for key in ("entrust", "position"):
            for kw in (panel_keywords.get(key) or []):
                if kw not in keywords:
                    keywords.append(kw)
        if expected_text:
            keywords.insert(0, expected_text)
        
        start = time.time()
        check_interval = 3  # 每3秒扫一次
        
        while time.time() - start < timeout:
            result = self.screen.read_text()
            if not result["ok"]:
                time.sleep(check_interval)
                continue
            
            screen_text = result.get("text", "")
            found = [kw for kw in keywords if kw in screen_text]
            
            if found:
                elapsed = round(time.time() - start, 1)
                L.info(f"👁 屏幕检测到: {found} (用时{elapsed}s)")
                entrust = self.detect_trade_panel_readback(panel="entrust", stock_code=code, broker=broker)
                position = self.detect_trade_panel_readback(panel="position", stock_code=code, broker=broker)
                return {
                    "ok": True,
                    "found": True,
                    "keywords": found,
                    "screen_text": screen_text[:300],
                    "elapsed": elapsed,
                    "entrust_state": entrust,
                    "position_state": position,
                }
            
            time.sleep(check_interval)
        
        entrust = self.detect_trade_panel_readback(panel="entrust", stock_code=code, broker=broker)
        position = self.detect_trade_panel_readback(panel="position", stock_code=code, broker=broker)
        return {
            "ok": True,
            "found": False,
            "screen_text": "",
            "elapsed": round(time.time() - start, 1),
            "message": f"{timeout}s内未检测到交易确认",
            "entrust_state": entrust,
            "position_state": position,
        }
    
    def voice_trade_announce(self, code, name, action, price, shares):
        """语音播报交易"""
        try:
            action_cn = "买入" if action == "buy" else "卖出"
            msg = f"{action_cn} {name}，{shares}股，价格{price}元"
            L.info(f"🗣 播报: {msg}")
            return self.voice.speak(msg)
        except Exception as e:
            L.error(f"voice_trade_announce FAILED: {e}")
            return {"ok": False, "error": str(e)}
    
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
