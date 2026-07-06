"""tests/test_mcp_stdio_bridge.py · MCP stdio 外部 AI 联测"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from _bp_helper import is_main_alive
from gbt.mcp import UniversalMCP


CONFIG_PATH = r"c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI\config\mcp-config.json"


@pytest.mark.skipif(not is_main_alive(), reason="desktop runtime not running")
def test_mcp_stdio_bridge_ping_and_chat():
    client = UniversalMCP(config_path=CONFIG_PATH)
    assert "external_ai_stdio" in client.list_servers()

    ping = client.call("external_ai_stdio", "ping", timeout=20)
    assert ping.ok is True
    ping_body = json.loads(str(ping.data))
    assert ping_body["ok"] is True
    assert ping_body["provider_count"] >= 1

    chat = client.call("external_ai_stdio", "chat", "请只回复 MCP_OK", timeout=60)
    assert chat.ok is True
    chat_body = json.loads(str(chat.data))
    assert chat_body["ok"] is True
    assert chat_body.get("provider")
    assert chat_body.get("model")
    assert "MCP_OK" in (chat_body.get("response") or "")
