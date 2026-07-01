"""GBT AI Vision Service"""
import os, io, base64, logging, time
import pyautogui
from PIL import Image
L = logging.getLogger("GBT.Vision")

class VisionService:
    def screenshot(self, region=None, save_path=None):
        try:
            img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                img.save(save_path)
            return img
        except Exception as e:
            L.error(f"screenshot failed: {e}")
            return None

    def ocr(self, image):
        try:
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.graphics.imaging import BitmapDecoder
            from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
            eng = OcrEngine.try_create_from_user_profile_languages()
            if not eng:
                eng = OcrEngine.try_create_from_language(OcrEngine.available_recognizer_languages[0])
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            stream = InMemoryRandomAccessStream()
            writer = DataWriter(stream)
            writer.write_bytes(buf.getvalue())
            writer.store_async()
            writer.detach_stream()
            stream.seek(0)
            decoder = BitmapDecoder.create_async(stream).as_task().result()
            sb = decoder.get_software_bitmap_async().as_task().result()
            result = eng.recognize_async(sb).as_task().result()
            text = result.text if result else ""
            lines = [l.text for l in (result.lines if result else [])]
            return {"ok": True, "text": text, "lines": lines}
        except Exception as e:
            return {"ok": False, "error": str(e), "text": ""}

    def describe(self, image, prompt="Describe the screen"):
        try:
            buf = io.BytesIO()
            image.save(buf, format="PNG", optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        glm_key = os.environ.get("GLM_API_KEY") or os.environ.get("ZHIPU_API_KEY")
        if glm_key:
            try:
                import requests
                url = "data:image/png;base64," + b64
                messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": url}}]}]
                r = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={"Authorization": f"Bearer {glm_key}", "Content-Type": "application/json"},
                    json={"model": "glm-4v", "messages": messages},
                    timeout=60)
                return {"ok": True, "provider": "glm-4v", "description": r.json()["choices"][0]["message"]["content"]}
            except Exception as e:
                L.warning(f"GLM-4V failed: {e}")
        return {"ok": False, "error": "No vision LLM available; set GLM_API_KEY"}

    def observe(self, region=None, save_path=None, use_llm=True, prompt=None):
        img = self.screenshot(region=region, save_path=save_path)
        if img is None:
            return {"ok": False, "error": "screenshot failed"}
        result = {"ok": True, "image_size": img.size, "timestamp": time.time(), "ocr": self.ocr(img)}
        if use_llm:
            p = prompt or "Detailed screen description in Chinese."
            llm = self.describe(img, prompt=p)
            result["llm"] = llm
            result["description"] = llm.get("description", "") if llm.get("ok") else result["ocr"].get("text", "")
        else:
            result["description"] = result["ocr"].get("text", "")
        return result
