#!/usr/bin/env python3
# 开发者：自由的风
# immutable_deploy.py - Atomic module deployment using immutable artifacts and route switch.
import os, sys, json, shutil, subprocess
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
ARTIFACTS = ROOT / 'artifacts'

def log(m): print(f'[IMMUTABLE] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def package_module(module_path, module_name, version='latest'):
    """Create immutable artifact package."""
    module_path=Path(module_path)
    artifact_dir=ARTIFACTS/module_name
    ensure_dir(artifact_dir)
    artifact=artifact_dir/f'{version}-{datetime.now().strftime("%Y%m%d-%H%M%S%f")}'
    ensure_dir(artifact)
    subprocess.run(f'robocopy "{module_path}" "{artifact}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1', shell=True, capture_output=True, timeout=300)
    manifest={'module': module_name, 'version': version, 'path': str(artifact), 'timestamp': datetime.now().isoformat()}
    (artifact/'artifact-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'artifact packaged: {artifact}')
    return str(artifact)

def atomic_switch(production_link, artifact_path, backup_path):
    """Switch production symlink/pointer to new immutable artifact atomically."""
    production_link=Path(production_link)
    if production_link.is_symlink() or production_link.exists():
        # backup current
        if production_link.is_symlink():
            current=production_link.resolve()
            if current.exists():
                subprocess.run(f'robocopy "{current}" "{backup_path}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1', shell=True, capture_output=True, timeout=300)
        elif production_link.is_dir():
            subprocess.run(f'robocopy "{production_link}" "{backup_path}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1', shell=True, capture_output=True, timeout=300)
        # remove old link/dir
        if production_link.is_symlink(): production_link.unlink()
        elif production_link.is_dir(): shutil.rmtree(production_link, ignore_errors=True)
    # Windows does not support directory symlinks without admin; use junction as fallback or rename
    try:
        subprocess.run(f'mklink /J "{production_link}" "{artifact_path}"', shell=True, check=True, capture_output=True, timeout=30)
        log(f'atomic switch: {production_link} -> {artifact_path}')
    except Exception:
        # fallback: rename
        shutil.copytree(artifact_path, production_link, dirs_exist_ok=True)
        log(f'atomic switch via copy: {production_link}')
    return True

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--module-path', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--version', default='latest')
    ap.add_argument('--production-link', required=True)
    ap.add_argument('--backup', required=True)
    args=ap.parse_args()
    art=package_module(args.module_path, args.name, args.version)
    ok=atomic_switch(args.production_link, art, args.backup)
    sys.exit(0 if ok else 1)
