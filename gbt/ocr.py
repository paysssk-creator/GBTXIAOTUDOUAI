"""
ocr.py — 图片转文字引擎
Tesseract + Windows OCR + EasyOCR 三引擎自动降级
让没有视觉能力的大模型也能\"看懂\"图片
"""

import os, base64, tempfile, subprocess, logging
from typing import Optional, List, Tuple

L = logging.getLogger("GBT.OCR")
from dataclasses import dataclass
from enum import Enum


class OCREngine(Enum):
    TESSERACT="tesseract"
    WINDOWS="windows"
    EASYOCR="easyocr"

@dataclass
class OCRResult:
    text: str; engine: OCREngine; confidence: float=0.0
    duration: float=0.0; lang: str=""


class ImageToText:
    """图片→文字 三引擎自动降级: Tesseract→EasyOCR→Windows"""

    def __init__(self, lang: str="chi_sim+eng"):
        self.lang = lang
        self._tess = self._find_tess()
        self._reader = None
        self._engs = self._detect()
        print(f"📖 OCR: {self._engs}")

    def _find_tess(self) -> str:
        for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")]:
            if os.path.exists(p): return p
        r = subprocess.run(["where", "tesseract"], shell=False, capture_output=True, text=True)
        return r.stdout.strip().split("\n")[0] if r.returncode == 0 else ""

    def _detect(self) -> List[str]:
        e = []; e.append("windows")
        if self._tess: e.insert(0, "tesseract")
        return e

    def recognize(self, image) -> OCRResult:
        """图片→文字 自动选最佳引擎"""
        import time; t0 = time.time()
        fp = self._resolve(image)
        if not fp: return OCRResult(text="[无效图片]", engine=OCREngine.WINDOWS)
        # 1. Tesseract
        if "tesseract" in self._engs:
            r = self._tess_ocr(fp)
            if r and len(r.strip())>3 and not r.startswith("Warning"):
                return OCRResult(text=r, engine=OCREngine.TESSERACT,
                               duration=time.time()-t0, lang=self.lang)
        # 2. EasyOCR
        try:
            r = self._easy_ocr(fp)
            if r and len(r.strip())>2:
                return OCRResult(text=r, engine=OCREngine.EASYOCR,
                               duration=time.time()-t0, lang=self.lang)
        except Exception as e:
            L.debug(f"EasyOCR 不可用，降级到 Windows OCR: {e}")
        # 3. Windows
        try:
            r = self._win_ocr(fp)
            return OCRResult(text=r or "(空白)", engine=OCREngine.WINDOWS,
                           duration=time.time()-t0, lang=self.lang)
        except Exception as e:
            return OCRResult(text=f"[OCR失败:{e}]", engine=OCREngine.WINDOWS)

    def ocr_screen(self) -> Tuple[OCRResult, str]:
        """截图+OCR一键"""
        import io
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO(); img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        fp = self._save(img)
        r = self.recognize(fp)
        if os.path.exists(fp): os.remove(fp)
        return r, b64

    def ocr_region(self, x, y, w, h) -> OCRResult:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(x,y,x+w,y+h))
        fp = self._save(img); r = self.recognize(fp)
        if os.path.exists(fp): os.remove(fp); return r

    def _resolve(self, img) -> str:
        if isinstance(img, str) and not img.startswith("data:"):
            return img if os.path.exists(img) else ""
        if isinstance(img, str) and "base64" in img:
            d = img.split("base64,")[-1] if "base64," in img else img
            fp = os.path.join(tempfile.gettempdir(), f"gbt_ocr.png")
            with open(fp,"wb") as f: f.write(base64.b64decode(d)); return fp
        if hasattr(img, "save"): return self._save(img)
        return str(img) if os.path.exists(str(img)) else ""

    def _save(self, img) -> str:
        fp = os.path.join(tempfile.gettempdir(), f"gbt_ocr_{id(img)}.png")
        img.save(fp, format="PNG"); return fp

    def _tess_ocr(self, fp: str) -> str:
        if not self._tess or not os.path.exists(fp): return ""
        try:
            r = subprocess.run([self._tess, fp, "stdout", "-l", self.lang, "--psm", "3"],
                shell=False, capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception as e:
            L.warning(f"Tesseract OCR failed: {e}")
            return ""

    def _win_ocr(self, fp: str) -> str:
        ps = f'''Add-Type -AssemblyName System.Drawing;[Reflection.Assembly]::LoadFrom("C:\\Windows\\System32\\Windows.Media.Ocr.dll")|Out-Null;$b=[System.Drawing.Bitmap]::FromFile("{fp}");$m=New-Object IO.MemoryStream;$b.Save($m,[Drawing.Imaging.ImageFormat]::Png);$s=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream;$w=New-Object Windows.Storage.Streams.DataWriter($s.GetOutputStreamAt(0));$w.WriteBytes($m.ToArray());$w.StoreAsync().GetAwaiter().GetResult();$d=[Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s).GetAwaiter().GetResult();$sw=[Windows.Graphics.Imaging.SoftwareBitmap]::Convert($d.GetSoftwareBitmapAsync().GetAwaiter().GetResult(),[Windows.Graphics.Imaging.BitmapPixelFormat]::Rgba8);$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();$e.Result.RecognizeAsync($sw).GetAwaiter().GetResult().Text;$b.Dispose();$m.Dispose();$s.Dispose()'''
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], shell=False, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""

    def _easy_ocr(self, fp: str) -> str:
        try:
            if self._reader is None:
                import easyocr; self._reader = easyocr.Reader(['ch_sim','en'], gpu=False)
            return "\n".join(t for _,t,_ in self._reader.readtext(fp))
        except Exception as e:
            L.debug(f"EasyOCR failed: {e}")
            return ""


_ocr: Optional[ImageToText] = None

def get_ocr(lang: str="chi_sim+eng") -> ImageToText:
    global _ocr
    if _ocr is None: _ocr = ImageToText(lang)
    return _ocr

def image_to_text(image) -> OCRResult:
    return get_ocr().recognize(image)

def screenshot_to_text() -> Tuple[str, str]:
    """截图→OCR→文字 text, base64"""
    r, b64 = get_ocr().ocr_screen()
    return r.text, b64

def ocr_pipeline_for_llm(image) -> str:
    """为LLM准备: 图片→OCR→格式化文本"""
    r = image_to_text(image)
    return f"[OCR文字提取 | {r.engine.value}引擎 | {r.duration:.1f}s]\n{r.text}"