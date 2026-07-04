#!/usr/bin/env python3
# 开发者：自由的风
# data_compat.py - Data layer isolation and compatibility verification.
import os, sys, json, hashlib
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'

def log(m): print(f'[DATA-COMPAT] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def scan_schema_files(path):
    """Find JSON schema, TypeScript types, SQL DDL files."""
    schemas=[]
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git','__pycache__','dist','build'}]
        for fn in files:
            if fn.endswith(('.schema.json','.sql','.prisma','.ddl')) or fn in ['schema.json','types.ts']:
                schemas.append(str(Path(root)/fn))
    return schemas

def data_checksum(path):
    h=hashlib.sha256()
    for fp in sorted(Path(path).rglob('*')):
        if fp.is_file() and fp.suffix in ['.json','.db','.sqlite','.csv']:
            h.update(fp.read_bytes())
    return h.hexdigest()[:16]

def check_data_compatibility(old_module_path, new_module_path):
    """Verify data schemas are compatible between old and new module."""
    old_schemas=scan_schema_files(old_module_path)
    new_schemas=scan_schema_files(new_module_path)
    report={
        'old_schemas': old_schemas,
        'new_schemas': new_schemas,
        'old_checksum': data_checksum(old_module_path),
        'new_checksum': data_checksum(new_module_path),
        'ok': True,
        'notes': []
    }
    # naive check: if schema file count dropped, flag it
    if len(new_schemas) < len(old_schemas):
        report['ok']=False
        report['notes'].append('schema files removed')
    # if no schema files found, warn but allow
    if not new_schemas:
        report['notes'].append('no schema files detected, cannot verify compatibility')
    log(f'data compat: old={report["old_checksum"]} new={report["new_checksum"]} ok={report["ok"]}')
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    args=ap.parse_args()
    r=check_data_compatibility(args.old, args.new)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    sys.exit(0 if r['ok'] else 1)
