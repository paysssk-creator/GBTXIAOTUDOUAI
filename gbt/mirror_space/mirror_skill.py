#!/usr/bin/env python3
# 开发者：自由的风
# mirror-skill.py - Active skill: precise insertion of mirror multi-dimensional space into any Agent workflow.
# Usage: mirror-skill --project <path> [--evolve] [--canary] [--monitor] [--rollback <module>]
import os, sys, subprocess, json
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
BIN = HOME / '.gbt' / 'sandbox' / 'bin'

def log(m): print(f'[MIRROR-SKILL] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def run(cmd, cwd=None, t=1200):
    log(f'run: {cmd}')
    r=subprocess.run(cmd, cwd=cwd or str(BIN), shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=t)
    out=(r.stdout or '') + (r.stderr or '')
    return r.returncode, out

def main():
    args=sys.argv[1:]
    if '--project' not in args:
        log('ERROR: --project required'); sys.exit(1)
    project=args[args.index('--project')+1]
    dry_run='--dry-run' in args
    if '--rollback' in args:
        mod=args[args.index('--rollback')+1]
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --rollback --module {mod}')
        print(out); sys.exit(rc)
    if '--monitor' in args:
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --monitor')
        print(out); sys.exit(rc)
    if '--rollback-drill' in args:
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --rollback-drill')
        print(out); sys.exit(rc)
    if '--validate' in args:
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --validate')
        print(out); sys.exit(rc)
    if '--canary' in args:
        # full -> canary deploy
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --full --deploy')
        if rc!=0: print(out); sys.exit(rc)
        rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --canary {"--dry-run" if dry_run else ""}')
        print(out); sys.exit(rc)
    # default: full pipeline with reasoning + test + deploy
    evolve='--evolve' in args
    rc,out=run(f'python sandbox-orchestrator.py --project "{project}" --full --deploy {"--evolve" if evolve else ""} {"--dry-run" if dry_run else ""}')
    print(out); sys.exit(rc)

if __name__=='__main__':
    main()
