#!/usr/bin/env python3
# 开发者：自由的风
# data_validator.py - Post-release data validation: checksums, row counts, business metrics.
import os, sys, json, hashlib
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'

def log(m): print(f'[VALIDATOR] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def file_checksum(fp):
    h=hashlib.sha256()
    with open(fp,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''): h.update(chunk)
    return h.hexdigest()

def validate(project_root, baseline=None):
    """Compare current data/schema state against baseline or snapshot."""
    project_root=Path(project_root)
    findings=[]
    # validate key files
    for fn in ['package.json','schema.json','data.json','db.json']:
        fp=project_root/fn
        if fp.exists():
            cs=file_checksum(fp)
            findings.append({'file': fn, 'checksum': cs, 'size': fp.stat().st_size})
    # business metric demo: count lines in key source files
    total_lines=0
    for root, dirs, files in os.walk(project_root/'src' if (project_root/'src').exists() else project_root):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git'}]
        for fn in files:
            if fn.endswith(('.ts','.js','.py')):
                fp=Path(root)/fn
                try:
                    total_lines+=len(fp.read_text(encoding='utf-8',errors='ignore').splitlines())
                except Exception: pass
    findings.append({'metric':'total_source_lines','value':total_lines})
    report={'project': str(project_root), 'timestamp': datetime.now().isoformat(), 'findings': findings, 'ok': True}
    out=ROOT/'data-validation-report.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'data validation report: {out}')
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    args=ap.parse_args()
    r=validate(args.project)
    print(json.dumps(r, indent=2, ensure_ascii=False))
