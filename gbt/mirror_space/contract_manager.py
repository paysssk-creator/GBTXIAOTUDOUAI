#!/usr/bin/env python3
# 开发者：自由的风
# contract_manager.py - Stable inter-module interface contracts, versioning and compatibility checks.
import os, sys, json, re, hashlib
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
CONTRACTS = ROOT / 'contracts'

def log(m): print(f'[CONTRACT] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def extract_exports(module_path):
    """Extract exported function/class signatures and event names from TS/JS."""
    exports=[]; events=[]
    for root, dirs, files in os.walk(module_path):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git','__pycache__','dist','build'}]
        for fn in files:
            if not fn.endswith(('.ts','.js','.tsx','.jsx')): continue
            fp=Path(root)/fn
            try:
                text=fp.read_text(encoding='utf-8',errors='ignore')
                # function exports
                for m in re.finditer(r'export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', text):
                    exports.append({'kind':'function','name':m.group(1),'args':m.group(2).strip()})
                for m in re.finditer(r'export\s+(?:default\s+)?(?:class|interface)\s+(\w+)', text):
                    exports.append({'kind':'type','name':m.group(1)})
                # event names
                events += re.findall(r"emit\s*\(\s*['\"]([^'\"]+)['\"]", text)
                events += re.findall(r"on\s*\(\s*['\"]([^'\"]+)['\"]", text)
            except Exception: pass
    return {'exports': sorted(exports, key=lambda x: x['name']), 'events': sorted(set(events))}

def contract_hash(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:16]

def build_contract(module_path, module_name, version='1.0.0'):
    contract=extract_exports(module_path)
    contract['module']=module_name
    contract['version']=version
    contract['timestamp']=datetime.now().isoformat()
    contract['hash']=contract_hash(contract)
    ensure_dir(CONTRACTS)
    fp=CONTRACTS/f'{module_name}-contract.json'
    fp.write_text(json.dumps(contract, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'contract built: {fp} hash={contract["hash"]}')
    return contract

def load_previous_contract(module_name):
    fp=CONTRACTS/f'{module_name}-contract.json'
    if fp.exists(): return json.loads(fp.read_text(encoding='utf-8'))
    return None

def check_compatibility(new_contract, old_contract):
    """Check new contract is backward compatible with old."""
    if not old_contract: return {'ok': True, 'reason': 'no previous contract'}
    issues=[]
    old_exports={(e.get('kind'),e.get('name')) for e in old_contract.get('exports',[])}
    new_exports={(e.get('kind'),e.get('name')) for e in new_contract.get('exports',[])}
    removed=old_exports - new_exports
    if removed: issues.append(f'removed exports: {removed}')
    old_events=set(old_contract.get('events',[]))
    new_events=set(new_contract.get('events',[]))
    removed_events=old_events - new_events
    if removed_events: issues.append(f'removed events: {removed_events}')
    ok=len(issues)==0
    return {'ok': ok, 'reason': '; '.join(issues) if issues else 'backward compatible'}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-module', required=True, help='path to module')
    ap.add_argument('--name', required=True)
    ap.add_argument('--version', default='1.0.0')
    args=ap.parse_args()
    old=load_previous_contract(args.name)
    new=build_contract(args.project_module, args.name, args.version)
    result=check_compatibility(new, old)
    log(f'compatibility: {result["reason"]}')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['ok'] else 1)
