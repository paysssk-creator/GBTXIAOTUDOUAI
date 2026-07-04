#!/usr/bin/env python3
# 开发者：自由的风
# env_lock.py - Lock runtime, library and system dependency versions for environment consistency.
import os, sys, json, subprocess, re
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'

def log(m): print(f'[ENV-LOCK] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def detect_runtime(project_root):
    """Detect runtime versions."""
    info={'node':None,'npm':None,'bun':None,'python':None}
    try:
        out=subprocess.run('node --version', shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
        info['node']=out
    except Exception: pass
    try:
        out=subprocess.run('npm --version', shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
        info['npm']=out
    except Exception: pass
    try:
        out=subprocess.run('bun --version', shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
        info['bun']=out
    except Exception: pass
    try:
        out=subprocess.run('python --version', shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
        info['python']=out
    except Exception: pass
    return info

def lock_dependencies(project_root):
    """Generate environment lock manifest."""
    project_root=Path(project_root)
    manifest={
        'project': str(project_root),
        'timestamp': datetime.now().isoformat(),
        'runtimes': detect_runtime(project_root),
        'files': {}
    }
    # package-lock
    for fn in ['bun.lock','package-lock.json','yarn.lock','pnpm-lock.yaml']:
        fp=project_root/fn
        if fp.exists():
            manifest['files'][fn]=str(fp)
            break
    # py requirements
    for fn in ['requirements.txt','requirements.lock','poetry.lock']:
        fp=project_root/fn
        if fp.exists():
            manifest['files'][fn]=str(fp)
            break
    # docker / infra
    for fn in ['Dockerfile','docker-compose.yml','.nvmrc','.tool-versions']:
        fp=project_root/fn
        if fp.exists():
            manifest['files'][fn]=str(fp)
    # runtime constraints
    manifest['constraints']={
        'node': '>=20.0.0',
        'npm': '>=10.0.0',
        'python': '>=3.11'
    }
    out=ROOT/'env-lock.json'
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'environment lock written: {out}')
    return manifest

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    args=ap.parse_args()
    m=lock_dependencies(args.project)
    print(json.dumps(m, indent=2, ensure_ascii=False))
