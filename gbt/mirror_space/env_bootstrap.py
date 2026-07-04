#!/usr/bin/env python3
# 开发者：自由的风
# env_bootstrap.py - Bootstrap standardized sandbox environment from lock manifest and templates.
import os, sys, json, subprocess, shutil
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'

def log(m): print(f'[ENV-BOOTSTRAP] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def bootstrap(project_root):
    """Create or verify sandbox environment matches production."""
    project_root=Path(project_root)
    lock_file=ROOT/'env-lock.json'
    if not lock_file.exists():
        log('env-lock.json missing, run env_lock first'); return False
    lock=json.loads(lock_file.read_text(encoding='utf-8'))
    env_dir=ROOT/'env'/project_root.name
    ensure_dir(env_dir)
    # copy config templates
    for src_rel in lock.get('files',{}).values():
        src=Path(src_rel)
        if src.exists():
            dst=env_dir/src.name
            shutil.copy2(src, dst)
    # verify runtime versions
    runtimes=lock.get('runtimes',{})
    for name, expected in runtimes.items():
        if not expected: continue
        try:
            actual=subprocess.run(f'{name} --version', shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
            if expected.split()[0] not in actual and actual.split()[0] not in expected:
                log(f'WARNING runtime mismatch {name}: expected {expected}, got {actual}')
        except Exception as e:
            log(f'WARNING cannot verify {name}: {e}')
    # write env template if missing
    env_template=project_root/'.env.template'
    env_example=project_root/'.env.example'
    if env_example.exists() and not env_template.exists():
        shutil.copy2(env_example, env_template)
    manifest={'project': str(project_root), 'env_dir': str(env_dir), 'runtimes': runtimes, 'timestamp': datetime.now().isoformat()}
    (env_dir/'bootstrap-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'sandbox environment bootstrapped: {env_dir}')
    return True

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    args=ap.parse_args()
    r=bootstrap(args.project)
    sys.exit(0 if r else 1)
