#!/usr/bin/env python3
# 开发者：自由的风
# migration_manager.py - Paired forward/backward/idempotent data and schema migrations.
import os, sys, json, re, shutil
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
MIGRATIONS = ROOT / 'migrations'

def log(m): print(f'[MIGRATION] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def list_migrations():
    """Return sorted migration scripts."""
    if not MIGRATIONS.exists(): return []
    files=[]
    for f in MIGRATIONS.glob('*.py'):
        m=re.match(r'(\d+)_(.+)', f.name)
        if m: files.append((int(m.group(1)), f))
    return sorted(files)

def snapshot(project_root):
    """Create a snapshot of data/schemas before migration."""
    snap_dir=ROOT/'snapshots'/f'{Path(project_root).name}-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    ensure_dir(snap_dir)
    # snapshot package.json / schema-like files as demo
    for fn in ['package.json','schema.json','data.json','db.json']:
        src=Path(project_root)/fn
        if src.exists(): shutil.copy2(src, snap_dir/fn)
    log(f'snapshot created: {snap_dir}')
    return str(snap_dir)

def run_migration(mig_file, direction='up', dry_run=False):
    """Run a single migration file."""
    log(f'{"DRY-RUN " if dry_run else ""}{direction}: {mig_file.name}')
    if dry_run: return True
    # exec migration module
    spec=__import__('importlib.util').util.spec_from_file_location('mig', str(mig_file))
    mig=__import__('importlib.util').util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    fn=getattr(mig, direction, None)
    if not fn:
        log(f'  no {direction} function, skipping')
        return True
    try:
        fn()
        log('  OK')
        return True
    except Exception as e:
        log(f'  FAIL: {e}')
        return False

def migrate(project_root, direction='up', dry_run=False):
    """Run migrations with snapshot and idempotency."""
    project_root=Path(project_root)
    snap=snapshot(project_root)
    state_file=ROOT/'migration-state.json'
    state=json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {'applied':[]}
    migs=list_migrations()
    if direction=='up':
        for ver, mig_file in migs:
            if ver in state['applied']:
                log(f'skip already applied: {mig_file.name}')
                continue
            if not run_migration(mig_file, 'up', dry_run): return False
            if not dry_run: state['applied'].append(ver)
    elif direction=='down':
        for ver, mig_file in reversed(migs):
            if ver not in state['applied'] and not dry_run:
                continue
            if not run_migration(mig_file, 'down', dry_run): return False
            if not dry_run and ver in state['applied']: state['applied'].remove(ver)
    state['last_snapshot']=snap
    state['timestamp']=datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log('migration state updated')
    return True

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--direction', choices=['up','down'], default='up')
    ap.add_argument('--dry-run', action='store_true')
    args=ap.parse_args()
    r=migrate(args.project, args.direction, args.dry_run)
    sys.exit(0 if r else 1)
