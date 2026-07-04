import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gbt.hf_space import build_space_bundle, get_saved_hf_config, save_hf_token


def test_save_hf_token_persists_on_device():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["GBT_DEVICE_DATA_DIR"] = tmp
        cfg = save_hf_token("hf_testtoken1234567890")
        saved = get_saved_hf_config()
        assert cfg["saved_on_device"] is True
        assert saved["saved_on_device"] is True
        assert saved["token_masked"].startswith("hf_tes")


def test_build_space_bundle_outputs_required_files():
    with tempfile.TemporaryDirectory() as tmp:
        target = build_space_bundle(tmp, space_title="GBT Cloud Brain", repo_url="https://example.com/repo")
        assert (target / "README.md").exists()
        assert (target / "Dockerfile").exists()
        assert (target / "requirements.txt").exists()
        assert (target / "app.py").exists()
        assert "app_port: 7860" in (target / "README.md").read_text(encoding="utf-8")
        assert "GBT Cloud Brain" in (target / "app.py").read_text(encoding="utf-8")
