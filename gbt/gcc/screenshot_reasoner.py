"""
screenshot_reasoner.py — 截图推理器 (借鉴Cradle Information Gathering)
截图→VLM分析界面→提取可交互元素→输出结构化信息
"""

import json
from typing import Optional, Dict, List

try:
    from ..llm import GBTLLM
except ImportError:
    try:
        from gbt.llm import GBTLLM
    except ImportError:
        GBTLLM = None


class ScreenshotReasoner:
    """截图+推理: 分析屏幕内容, 提取UI元素"""

    def __init__(self, llm: Optional[GBTLLM] = None):
        self.llm = llm
        self._runner = GCCRunner(llm=llm) if GCCRunner else None

    def reason(self, screenshot_b64: Optional[str], question: str = "") -> Dict:
        """分析截图, 返回结构化信息"""
        if not self.llm:
            return {"ok": False, "error": "No LLM configured"}

        if not screenshot_b64:
            return {"ok": False, "error": "No screenshot available"}

        msgs = [{"role": "system", "content":
            """分析截图返回JSON:
{
  "app": "应用名称",
  "title": "窗口标题",
  "elements": [{"type":"button/input/menu/text/image","text":"...","position":"左上/中间/右下"}],
  "state": "当前状态描述",
  "answer": "针对问题的回答"
}"""}]
        content = [
            {"type": "text", "text": f"问题: {question or '描述屏幕内容'}"},
            {"type": "image_url", "image_url":
                {"url": f"data:image/jpeg;base64,{screenshot_b64}"}}
        ]
        msgs.append({"role": "user", "content": content})

        try:
            raw = self.llm.invoke(msgs)
            s = raw.find("{"); e = raw.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(raw[s:e])
            return {"ok": True, "raw": raw}
        except Exception as e:
            return {"ok": False, "error": str(e), "raw": raw if 'raw' in dir() else ""}
