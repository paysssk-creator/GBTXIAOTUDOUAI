import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gbt.api import llm


def test_cloud_brain_mode_normalization():
    assert llm._normalize_cloud_mode("cloud") == "cloud"
    assert llm._normalize_cloud_mode("hybrid") == "cloud_preferred"
    assert llm._normalize_cloud_mode("whatever") == "local"


def test_cloud_brain_cfg_persistence(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="gbt_cloud_cfg_") as tmp:
        monkeypatch.setenv("GBT_DEVICE_DATA_DIR", tmp)
        llm._write_cloud_brain_cfg({
            "url": "https://example.hf.space",
            "enabled": True,
            "chat_mode": "cloud_preferred",
            "timeout_sec": 33,
            "updated_at": 123,
        })
        cfg = llm._cloud_brain_runtime_cfg()
        assert cfg["url"] == "https://example.hf.space"
        assert cfg["enabled"] is True
        assert cfg["chat_mode"] == "cloud_preferred"
        assert cfg["timeout_sec"] == 33
        assert cfg["saved_on_device"] is True


def test_cloud_brain_default_url(monkeypatch):
    monkeypatch.delenv("GBT_CLOUD_BRAIN_URL", raising=False)
    assert llm._default_cloud_brain_url().startswith("https://")
