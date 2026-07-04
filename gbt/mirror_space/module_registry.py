#!/usr/bin/env python3
# 开发者：自由的风
# module-registry.py - Module decomposition, IO contracts and dependency graph.
import os, sys, json, re
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
REGISTRY = ROOT / 'module-registry.json'

WATERMARK = "# 开发者：自由的风\n"

def log(m): print(f'[REGISTRY] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def detect_module_interface(path):
    """Infer module inputs/outputs by scanning exports/imports."""
    p=Path(path)
    exports=[]; imports=[]
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git','__pycache__','.venv','venv','dist','build'}]
        for fn in files:
            fp=Path(root)/fn
            if fn.endswith(('.ts','.js','.tsx','.jsx')):
                try:
                    text=fp.read_text(encoding='utf-8',errors='ignore')
                    exports += re.findall(r'export\s+(?:default\s+)?(?:function|class|const|interface|type)\s+(\w+)', text)
                    imports += re.findall(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']', text)
                except Exception: pass
    return list(set(exports)), list(set(imports))

def build_registry(project_root):
    """Discover modules and write registry with contracts."""
    import importlib.util
    spec=importlib.util.spec_from_file_location('sandbox_orchestrator', str(ROOT/'bin'/'sandbox-orchestrator.py'))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    discover=mod.discover
    project_root=Path(project_root)
    mods=discover(project_root)
    registry={'project': str(project_root), 'modules': {}, 'dependencies': [], 'timestamp': datetime.now().isoformat()}
    for mod in mods:
        name=mod['name']
        exports, imports=detect_module_interface(mod['path'])
        registry['modules'][name]={
            'name': name,
            'type': mod['type'],
            'path': mod['path'],
            'outputs': sorted(exports),
            'inputs': sorted([i for i in imports if not i.startswith('.')]),
            'internal_deps': sorted([i for i in imports if i.startswith('.')])
        }
    # build dependency graph between local modules
    names=set(registry['modules'].keys())
    for name, info in registry['modules'].items():
        for dep in info.get('internal_deps',[]):
            dep_name=dep.split('/')[1] if dep.startswith('./') or dep.startswith('../') else dep
            if dep_name in names and dep_name != name:
                registry['dependencies'].append({'from': name, 'to': dep_name})
    registry['dependencies']=[dict(t) for t in {tuple(sorted(d.items())) for d in registry['dependencies']}]
    ensure_dir(REGISTRY.parent)
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    log(f'registry built: {REGISTRY}')
    return registry

def get_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding='utf-8'))
    return None

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    args=ap.parse_args()
    reg=build_registry(args.project)
    print(json.dumps(reg, indent=2, ensure_ascii=False))
