"""Deploy GBT Cloud Brain to Hugging Face Spaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gbt.hf_space import (
    discover_cloud_secrets,
    get_saved_hf_config,
    load_hf_token,
    save_hf_token,
    stage_space_bundle,
)


def parse_args():
    ap = argparse.ArgumentParser(description="Deploy GBT Cloud Brain to Hugging Face Spaces")
    ap.add_argument("--space-name", default="gbt-cloud-brain")
    ap.add_argument("--title", default="GBT Cloud Brain")
    ap.add_argument("--owner", default="")
    ap.add_argument("--token", default="")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--repo-url", default="https://github.com/paysssk-creator/GBTXIAOTUDOUAI")
    return ap.parse_args()


def main():
    args = parse_args()
    token = (args.token or load_hf_token()).strip()
    if not token:
        raise SystemExit("HF token not found. Pass --token once to save it on device.")
    if args.token:
        save_hf_token(args.token)

    try:
        from huggingface_hub import HfApi
    except Exception as exc:
        raise SystemExit("Missing dependency huggingface_hub. Run: pip install huggingface_hub") from exc

    api = HfApi(token=token)
    who = api.whoami()
    owner = (args.owner or who.get("name") or "").strip()
    if not owner:
        raise SystemExit("Unable to resolve Hugging Face owner name")

    repo_id = f"{owner}/{args.space_name}"
    bundle_dir = stage_space_bundle(space_title=args.title, repo_url=args.repo_url)
    secret_map = discover_cloud_secrets()

    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
        private=bool(args.private),
    )

    api.upload_folder(
        folder_path=str(bundle_dir),
        repo_id=repo_id,
        repo_type="space",
        commit_message="Deploy GBT Cloud Brain",
    )

    api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value=token)
    for key, value in secret_map.items():
        if key.endswith("API_KEY"):
            api.add_space_secret(repo_id=repo_id, key=key, value=value)
        else:
            api.add_space_variable(repo_id=repo_id, key=key, value=value)
    api.add_space_variable(repo_id=repo_id, key="GBT_RELEASE_TAG", value="hf-space-cloud-brain")
    api.add_space_variable(repo_id=repo_id, key="GBT_REPO_URL", value=args.repo_url)

    result = {
        "ok": True,
        "repo_id": repo_id,
        "space_url": f"https://huggingface.co/spaces/{repo_id}",
        "saved_hf": get_saved_hf_config(),
        "uploaded_files": sorted(p.name for p in bundle_dir.iterdir()),
        "cloud_secret_keys": sorted(secret_map.keys()),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
