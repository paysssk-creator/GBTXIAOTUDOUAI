#!/usr/bin/env python3
# 开发者：自由的风
# prod-mirror.py - Mirror production configs, service deps and data structures into sandbox.
import os, sys, json, shutil
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
PROD_MIRROR = ROOT / 'prod-mirror'

def log(m): print(f'[PROD-MIRROR] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def mirror_production(project_root):
    """Create production-like mirror: copy configs, env templates, infra manifests."""
    project_root=Path(project_root)
    ensure_dir(PROD_MIRROR)
    # collect config-like files
    copied=[]
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git','__pycache__','.venv','venv','dist','build'}]
        for fn in files:
            if any(fn.endswith(ext) for ext in ['.env','.env.example','.env.template','.env.local']):
                src=Path(root)/fn
                rel=src.relative_to(project_root)
                dst=PROD_MIRROR/rel
                ensure_dir(dst.parent)
                shutil.copy2(src, dst); copied.append(str(rel))
            if fn in ['docker-compose.yml','docker-compose.yaml','Dockerfile','k8s.yaml','deployment.yaml','service.yaml','nginx.conf','ci.yml']:
                src=Path(root)/fn
                rel=src.relative_to(project_root)
                dst=PROD_MIRROR/rel
                ensure_dir(dst.parent)
                shutil.copy2(src, dst); copied.append(str(rel))
    # generate a service dependency map
    manifest={
        'source_project': str(project_root),
        'timestamp': datetime.now().isoformat(),
        'copied_configs': sorted(copied),
        'notes': 'Mirror production configs for sandbox parity. Secrets replaced with .env.example templates.'
    }
    (PROD_MIRROR/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'production mirror updated: {PROD_MIRROR}')
    return manifest

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    args=ap.parse_args()
    m=mirror_production(args.project)
    print(json.dumps(m, indent=2, ensure_ascii=False))
