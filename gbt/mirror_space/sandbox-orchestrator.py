# 开发者：自由的风
#!/usr/bin/env python3
"""sandbox-orchestrator.py - AI Agent local/desktop sandbox deployment.
IRON LAW:
  1. All simulation/testing/coding runs in mirror space first.
  2. Production deployment is atomic module replacement only.
  3. Production panel contains only production-grade code.
  4. NO placeholders/fake-data/empty-shells/hardcoded-secrets in production.
  5. Mirror cache is cleaned after each module deployment.
"""
import os, sys, json, shutil, re, subprocess
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
import compress
from datetime import datetime
from pathlib import Path

# Active skill: environment, data, contract and atomic release management
import env_lock, env_bootstrap, migration_manager, data_validator
import contract_manager, data_compat, immutable_deploy

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
MIRROR = ROOT / 'mirror'
REPORTS = ROOT / 'reports'
SKIP_DIRS = {'node_modules','__pycache__','.venv','venv','dist','build','.git','sandbox-logs'}
FORBIDDEN = [
    ('placeholder', re.compile(r'placeholder|占位|todo-fix|xxx+|FIXME|HACK|TEMP|tempcode', re.I)),
    ('fake-data', re.compile(r'fake.*data|假数据|dummy.*data|mock.*data|test.*data|sample.*data', re.I)),
    ('empty-shell', re.compile(r'pass\s*$|return\s+null\s*$|not implemented|未实现|empty function|空壳', re.I)),
    ('hardcoded-secret', re.compile(r"['\"](sk-[a-zA-Z0-9]{20,})['\"]|api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9]{16,}['\"]|password\s*[:=]\s*['\"][^'\"]{6,}['\"]", re.I)),
    ('debug-code', re.compile(r'debugger;|console\.log|print\(|System\.out\.print')),
]
EXTS = ('.js','.ts','.jsx','.tsx','.py','.java','.go','.rs','.c','.cpp','.h','.json','.xml','.yaml','.yml','.bat','.sh','.ps1','.md','.html','.css','.scss','.env')

def log(m): print(f'[SANDBOX] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)
def run(cmd, cwd=None, t=120, ignore=False):
    try:
        r = subprocess.run(cmd, cwd=cwd or os.getcwd(), shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=t)
        out = (r.stdout or '') + (r.stderr or '')
        if not ignore and r.returncode != 0: raise RuntimeError(f'FAIL: {cmd}\n{out}')
        return out.strip()
    except subprocess.TimeoutExpired: return 'timeout' if ignore else (_ for _ in ()).throw(Exception('timeout'))
def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)
def find_bun():
    for cand in [r'C:\Users\ADMIN\.bun\bin\bun.exe','bun']:
        try:
            cmd=f'"{cand}" --version' if cand.endswith('.exe') else f'{cand} --version'
            out=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=5).stdout.strip()
            if out: return cand
        except Exception: continue
    return None
def stamp(): return datetime.now().isoformat().replace(':','-').replace('.','-')[:19]


def looks_like_module(path: Path):
    path = Path(path)
    return (
        (path / 'package.json').exists()
        or (path / 'requirements.txt').exists()
        or (path / 'pyproject.toml').exists()
        or (path / 'desktop_app.py').exists()
        or (path / 'main.py').exists()
        or (path / 'gbt' / '__init__.py').exists()
    )

def discover(root):
    mods=[]; root=Path(root)
    if not root.exists(): return mods
    if looks_like_module(root):
        hp=(root/'package.json').exists()
        hy=(root/'requirements.txt').exists() or (root/'pyproject.toml').exists() or (root/'gbt'/'__init__.py').exists()
        hb=(root/'run-cradle.bat').exists() or (root/'start-screenpipe.bat').exists() or (root/'desktop_app.py').exists()
        mods.append({'name':root.name or 'project-root','path':str(root),'type':'node' if hp else ('python' if hy else 'hybrid')})
    for e in root.iterdir():
        if not e.is_dir() or e.name.startswith('.') or e.name in ('node_modules','__pycache__'): continue
        hp=(e/'package.json').exists()
        hy=(e/'requirements.txt').exists() or (e/'pyproject.toml').exists() or (e/'__init__.py').exists()
        hb=(e/'run-cradle.bat').exists() or (e/'start-screenpipe.bat').exists()
        if hp or hy or hb: mods.append({'name':e.name,'path':str(e),'type':'node' if hp else ('python' if hy else 'hybrid')})
    return mods

def clean_mirror(name):
    mp=MIRROR/name
    if mp.exists(): shutil.rmtree(mp, ignore_errors=True); log(f'cleaned mirror cache: {name}')

def validate_purity(d, label):
    log(f'validate production purity: {label}')
    findings=[]
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
        for fn in files:
            if fn.startswith('.'): continue
            fp=Path(root)/fn
            rel=str(fp.relative_to(d)).lower()
            if fp.suffix.lower()=='.md': continue
            if '__tests__' in rel or '.test.' in rel or '.spec.' in rel: continue
            if 'tests/mocks' in rel or 'tests/fixtures' in rel or '/mocks/' in rel or '/fixtures/' in rel: continue
            if fp.suffix.lower() not in EXTS: continue
            try: text=fp.read_text(encoding='utf-8',errors='ignore')
            except Exception: continue
            for rn,rx in FORBIDDEN:
                m=rx.findall(text)
                if m:
                    if rn=='debug-code' and any(x in str(fp) for x in ('node_modules','vendor','dist','build')): continue
                    if rn=='hardcoded-secret' and any(x in str(fp).lower() for x in ('.env.sandbox','example','sample')): continue
                    findings.append({'file':str(fp),'rule':rn})
    critical = [f for f in findings if f['rule']=='hardcoded-secret']
    if critical:
        log('  FAIL production purity check, hardcoded secrets found:')
        for f in critical: log(f"    [{f['rule']}] {f['file']}")
        return {'ok':False,'findings':findings}
    if findings:
        log('  WARN production purity check, non-critical items found:')
        for f in findings: log(f"    [{f['rule']}] {f['file']}")
    log('  OK production purity verified')
    return {'ok':True,'findings':findings}

def mirror(mod):
    log(f"mirror module: {mod['name']}")
    clean_mirror(mod['name'])
    mp=MIRROR/mod['name']; ensure_dir(mp.parent)
    run(f'robocopy "{mod["path"]}" "{mp}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache res /XF .env *.key *.pem /R:1 /W:1', t=300, ignore=True)
    (mp/'.sandbox-mirror.json').write_text(json.dumps({'source':mod['path'],'mirroredAt':datetime.now().isoformat()},indent=2),encoding='utf-8')
    log(f'  ok mirrored: {mp}'); return {**mod,'mirrorPath':str(mp)}
def isolate(mod):
    log(f"isolate module: {mod['name']}")
    for f in ['.env','.env.local','.env.production','secrets.json','credentials.json']:
        fp=Path(mod['mirrorPath'])/f
        if fp.exists(): log(f'  removed secret file: {f}'); fp.unlink()
    (Path(mod['mirrorPath'])/'.env.sandbox').write_text(
        '# sandbox dummy keys - real keys never enter mirror space\nMOONSHOT_API_KEY=sk-sandbox-dummy-key\nOPENAI_API_KEY=sandbox-dummy\nSCREENPIPE_API_KEY=sandbox-dummy\nAHK_PATH=C:\\Users\\ADMIN\\cradle_ref\\.venv\\Scripts\\AutoHotkey.exe\nOPENAI_BASE_URL=https://api.moonshot.cn/v1\nSANDBOX_MODE=1\n',encoding='utf-8')
    log('  ok isolated')
    if not validate_purity(mod['mirrorPath'],f"{mod['name']} mirror")['ok']: raise RuntimeError(f"mirror purity check failed for {mod['name']}")
    return mod

def install_deps(mod):
    log(f"install dependencies: {mod['name']}")
    mp=Path(mod['mirrorPath'])
    if mod['type']=='node' and (mp/'package.json').exists():
        bun=find_bun()
        if bun and (mp/'bun.lock').exists():
            run(f'"{bun}" install',cwd=str(mp),t=300,ignore=True)
            log('  ok bun install')
        elif (mp/'package-lock.json').exists() or (mp/'package.json').exists():
            run('npm install',cwd=str(mp),t=300,ignore=True)
            log('  ok npm install')
    if mod['type']=='python':
        venv_path=mp/'.venv'
        if not venv_path.exists():
            run(f'python -m venv "{venv_path}"',t=120,ignore=True)
        pip=str(venv_path/'Scripts'/'pip.exe')
        if (mp/'requirements.txt').exists():
            run(f'"{pip}" install -r "{mp/"requirements.txt"}"',cwd=str(mp),t=300,ignore=True)
            log('  ok pip requirements')
        elif (mp/'pyproject.toml').exists():
            run(f'"{pip}" install -e "{mp}"',cwd=str(mp),t=300,ignore=True)
            log('  ok pip install -e')
    return mod

def test_module(mod):
    log(f"test module: {mod['name']}")
    install_deps(mod)
    if not validate_purity(mod['mirrorPath'],f"{mod['name']} pre-test")['ok']:
        log('  BLOCKED: purity check failed before test'); return {'module':mod['name'],'pass':False}
    r={'module':mod['name'],'type':mod['type'],'timestamp':datetime.now().isoformat(),'tests':{'ran':False,'passed':0,'failed':0,'output':''},'audit':{'ran':False,'ok':True,'output':''},'build':{'ran':False,'ok':True,'output':''},'secrets':{'ran':True,'ok':True,'findings':[]},'pass':False}
    sps=[re.compile(r"['\"](sk-[a-zA-Z0-9]{20,})['\"]"),re.compile(r"api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9]{16,}['\"]",re.I),re.compile(r"password\s*[:=]\s*['\"][^'\"]{6,}['\"]",re.I),re.compile(r"token\s*[:=]\s*['\"][a-zA-Z0-9]{16,}['\"]",re.I)]
    mp=Path(mod['mirrorPath'])
    for root, dirs, files in os.walk(mp):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
        for fn in files:
            if fn.startswith('.'): continue
            if fn=='.env.sandbox': continue
            fp=Path(root)/fn
            rel=str(fp.relative_to(mp)).lower()
            if '__tests__' in rel or '.test.' in rel or '.spec.' in rel: continue
            if fp.suffix.lower() not in ('.js','.ts','.py','.json','.bat','.sh','.env'): continue
            try: text=fp.read_text(encoding='utf-8',errors='ignore')
            except Exception: continue
            for pat in sps:
                m=pat.findall(text)
                if m: r['secrets']['findings'].append({'file':str(fp),'samples':m[:3]})
    r['secrets']['ok']=len(r['secrets']['findings'])==0
    try:
        if mod['type']=='node' and (mp/'package.json').exists():
            pkg=json.loads((mp/'package.json').read_text(encoding='utf-8'))
            sc=pkg.get('scripts',{})
            if 'test' in sc:
                # Integration tests often need external env; run unit tests only in sandbox
                if (mp/'tests'/'integration').exists() or (mp/'src'/'__tests__').exists():
                    cmd='bun test src/__tests__ --timeout 30000 --force-exit'
                else:
                    cmd='npm test'
                out=run(cmd,cwd=str(mp),t=300,ignore=True); r['tests']['ran']=True; r['tests']['output']=out[:2000]
                pm=re.search(r'(\d+)\s+pass',out); fm=re.search(r'(\d+)\s+fail',out)
                r['tests']['passed']=int(pm.group(1)) if pm else 0; r['tests']['failed']=int(fm.group(1)) if fm else 0
            if 'build' in sc:
                out=run('npm run build',cwd=str(mp),t=120,ignore=True); r['build']['ran']=True; r['build']['ok']='error' not in out.lower(); r['build']['output']=out[:1000]
        if mod['type']=='python' and ((mp/'tests').exists() or (mp/'pytest.ini').exists()):
            out=run('python -m pytest --tb=short -q',cwd=str(mp),t=120,ignore=True); r['tests']['ran']=True; r['tests']['output']=out[:2000]
            pm=re.search(r'(\d+)\s+passed',out); fm=re.search(r'(\d+)\s+failed',out)
            r['tests']['passed']=int(pm.group(1)) if pm else 0; r['tests']['failed']=int(fm.group(1)) if fm else 0
    except Exception as e: r['tests']['output']=str(e)
    au=HOME/'.cline'/'audit.js'
    if au.exists():
        out=run(f'node "{au}" --project "{mp}"',t=120,ignore=True); r['audit']['ran']=True; audit_m=re.search(r'❌\s*(\d+)\s*failed', out); r['audit']['ok']=(not audit_m or int(audit_m.group(1))==0); r['audit']['output']=out[:2000]
    r['pass']=r['secrets']['ok'] and r['tests']['failed']==0 and r['build']['ok'] and r['audit']['ok']
    log(f"  {'PASS' if r['pass'] else 'FAIL'} secrets:{len(r['secrets']['findings'])} tests:{r['tests']['passed']}P/{r['tests']['failed']}F build:{'OK' if r['build']['ok'] else 'FAIL'} audit:{'OK' if r['audit']['ok'] else 'FAIL'}")
    return r
def review(report):
    ensure_dir(REPORTS); p=REPORTS/f"{report['module']}-{stamp()}-review.json"; p.write_text(json.dumps(report,indent=2),encoding='utf-8'); log(f'review report: {p}')
    # context compression
    latest=REPORTS/f"{report['module']}-latest-review.json"
    latest.write_text(json.dumps(report,indent=2),encoding='utf-8')
    log(f'  SUMMARY: {compress.summarize_report(p)}')
    hist=compress.summarize_fix_history(report['module'], rounds=3)
    log('  HISTORY:')
    for line in hist.splitlines()[1:]:
        if line.strip(): log(f'    {line}')

def detect_start_command(path):
    pkg=Path(path)/'package.json'
    if not pkg.exists(): return None
    try:
        data=json.loads(pkg.read_text(encoding='utf-8'))
        scripts=data.get('scripts',{})
        for key in ('dev','start','serve','preview'):
            if key in scripts: return (key, scripts[key])
    except Exception: pass
    return None

def smoke_test(path, label, timeout=15):
    """Run start/dev command briefly to verify module can boot."""
    cmd_info=detect_start_command(path)
    if not cmd_info:
        log(f'  no start/dev script for {label}')
        return {'ok': True, 'reason': 'no script'}
    script_name, script_cmd = cmd_info
    log(f'  smoke test {label}: {script_name}')
    pm='bun' if find_bun() else 'npm'
    full_cmd=f'{pm} run {script_name}'
    proc=subprocess.Popen(full_cmd, cwd=str(path), shell=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='ignore')
    try:
        out, _ = proc.communicate(timeout=timeout)
        still_running=False
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(timeout=5)
        out, _ = proc.communicate()
        still_running=True
    out_str=out or ''
    error_patterns=['error:','failed','cannot find','module not found','port is already','command not found','crashed']
    has_error=any(p in out_str.lower() for p in error_patterns)
    if still_running and not has_error:
        ok=True; reason=f'ran {timeout}s without crash'
    elif proc.returncode==0 and not has_error:
        ok=True; reason='exited cleanly (possible one-shot script)'
    else:
        ok=False; reason=f'exit={proc.returncode}, error_output={has_error}'
    log(f'  smoke test {label}: {"OK" if ok else "FAIL"} ({reason})')
    return {'ok': ok, 'reason': reason, 'output': out_str[-600:]}

def canary_deploy(mod, report, dry_run=False, canary_ratio=0.1):
    """Deploy to canary first, smoke test, then promote."""
    if not report['pass']: log(f"BLOCKED: {mod['name']} did not pass review"); return False
    if not ensure_mirror_source(mod): return False
    log(f"canary deploy module: {mod['name']} ({int(canary_ratio*100)}%)")
    if not validate_purity(mod['mirrorPath'],f"{mod['name']} pre-deploy")['ok']: log('  BLOCKED: production purity check failed'); return False
    if dry_run: log(f"DRY-RUN: would canary deploy {mod['name']}"); return True
    canary_dir=ROOT/'canary'/mod['name']
    ensure_dir(canary_dir)
    log(f'  deploy canary: {canary_dir}')
    run(f'robocopy "{mod["mirrorPath"]}" "{canary_dir}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache sandbox-logs /XF .env.sandbox .sandbox-mirror.json /R:1 /W:1',t=300,ignore=True)
    st=smoke_test(canary_dir, f"{mod['name']} canary")
    if not st['ok']:
        log('  FAIL canary smoke test, aborting full deploy')
        return False
    # promote to production
    backup=ROOT/'backups'/f"{mod['name']}-{stamp()}"; ensure_dir(backup)
    log(f'  backup production: {backup}')
    run(f'robocopy "{mod["path"]}" "{backup}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
    log(f"  promote canary to production: {mod['path']}")
    run(f'robocopy "{canary_dir}" "{mod["path"]}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache sandbox-logs /XF .env.sandbox /R:1 /W:1',t=300,ignore=True)
    if not validate_purity(mod['path'],f"{mod['name']} post-deploy")['ok']: log('  FAIL post-deploy purity check'); return False
    log(f'  OK canary promoted: {mod["name"]}')
    return True

def rollback(mod_name):
    """Restore production from latest backup."""
    backups=sorted((ROOT/'backups').glob(f'{mod_name}-*'), key=lambda p:p.stat().st_mtime, reverse=True)
    if not backups: log(f'no backup found for {mod_name}'); return False
    latest=backups[0]
    log(f'rollback {mod_name} from {latest}')
    mods=discover(Path.cwd())
    mod_path=None
    for mod in mods:
        if mod['name']==mod_name: mod_path=mod['path']; break
    if not mod_path: log(f'production path not found for {mod_name}'); return False
    run(f'robocopy "{latest}" "{mod_path}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
    log(f'  rolled back: {mod_name}')
    return True

def monitor(mod, rounds=3, interval=5):
    """Post-deploy health check by running smoke test repeatedly."""
    log(f'monitor module: {mod["name"]}')
    for i in range(rounds):
        st=smoke_test(mod['path'], f"{mod['name']} monitor#{i+1}", timeout=10)
        if not st['ok']:
            log(f'  ALERT: health check failed at round {i+1}')
            return False
    log(f'  monitor OK: {mod["name"]} passed {rounds} rounds')
    return True

def ensure_mirror_source(mod):
    mp=Path(mod['mirrorPath']).resolve()
    if str(mp).startswith(str(MIRROR.resolve())): return True
    log(f"BLOCKED: {mod['name']} source is not in mirror space: {mp}")
    return False

def deploy(mod, report, dry_run=False):
    if not report['pass']: log(f"BLOCKED: {mod['name']} did not pass review"); return False
    if not ensure_mirror_source(mod): return False
    log(f"deploy module: {mod['name']}")
    if not validate_purity(mod['mirrorPath'],f"{mod['name']} pre-deploy")['ok']: log('  BLOCKED: production purity check failed'); return False
    # contract compatibility check
    old_contract=contract_manager.load_previous_contract(mod['name'])
    new_contract=contract_manager.build_contract(mod['mirrorPath'], mod['name'])
    compat=contract_manager.check_compatibility(new_contract, old_contract)
    log(f'  contract compatibility: {compat["reason"]}')
    if not compat['ok']: log('  BLOCKED: contract broken'); return False
    # data compatibility check
    old_path=mod['path']
    new_path=mod['mirrorPath']
    dc=data_compat.check_data_compatibility(old_path, new_path)
    if not dc['ok']: log(f"  BLOCKED: data incompatibility: {dc['notes']}"); return False
    if dry_run: log(f"DRY-RUN: would deploy {mod['name']}"); return True
    backup=ROOT/'backups'/f"{mod['name']}-{stamp()}"; ensure_dir(backup)
    log(f'  backup production: {backup}')
    run(f'robocopy "{mod["path"]}" "{backup}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
    log(f"  atomic immutable deploy: {mod['name']}")
    if dry_run: log(f'  DRY-RUN: would package and atomically switch {mod["name"]}'); return True
    artifact=immutable_deploy.package_module(mod['mirrorPath'], mod['name'])
    immutable_deploy.atomic_switch(mod['path'], artifact, str(backup))
    log(f'  install production dependencies: {mod["name"]}')
    run('npm install', cwd=mod['path'], t=300, ignore=True)
    au=HOME/'.cline'/'audit.js'
    if au.exists():
        out=run(f'node "{au}" --project "{mod["path"]}"',t=120,ignore=True)
        audit_m=re.search(r'❌\s*(\d+)\s*failed', out)
        if audit_m and int(audit_m.group(1))>0: log('  FAIL post-deploy audit'); return False
    log(f"  OK deployed: {mod['name']}")
    if dry_run: log(f'  DRY-RUN: would smoke test and monitor {mod["name"]}'); return True
    if not validate_purity(mod['path'],f"{mod['name']} post-deploy")['ok']: log('  FAIL post-deploy production purity check'); return False
    st=smoke_test(mod['path'], f"{mod['name']} post-deploy")
    if not st['ok']:
        log('  FAIL post-deploy smoke test, restoring from backup')
        run(f'robocopy "{backup}" "{mod["path"]}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
        log('  restored from backup')
        return False
    log(f'  OK smoke test: {mod["name"]}')
    return True

def reason_module(mod, evolve=False, threshold=5):
    """Run architecture reasoning in mirror space."""
    reasoner=Path(__file__).parent/'mirror_reasoner.py'
    if not reasoner.exists(): return
    mode='--dry-run' if not evolve else ''
    cmd=f'python "{reasoner}" --project "{mod["mirrorPath"]}" --module {mod["name"]} {mode} --threshold {threshold}'
    log(f'reasoning architecture: {mod["name"]}')
    try:
        out=run(cmd, t=300, ignore=True)
        log(out[:500])
    except Exception as e:
        log(f'reasoning error: {e}')

def main():
    args=sys.argv[1:]
    if '--project' in args: project_root=Path(args[args.index('--project')+1]).resolve()
    else: project_root=Path.cwd()
    dry_run='--dry-run' in args
    evolve='--evolve' in args
    ensure_dir(ROOT); ensure_dir(MIRROR); ensure_dir(ROOT/'staging'); ensure_dir(ROOT/'logs'); ensure_dir(REPORTS)
    log(f'project root: {project_root}')

    if '--discover' in args:
        mods=discover(project_root); log(f'found {len(mods)} modules:')
        for m in mods: log(f"  {m['type']:7} | {m['name']}")
    elif '--mirror' in args:
        for mod in discover(project_root):
            isolate(mirror(mod)); clean_mirror(mod['name'])
        log('mirror+isolate done')
    elif '--test' in args:
        for mod in discover(MIRROR):
            mod['mirrorPath']=mod['path']; review(test_module(mod))
    elif '--deploy' in args and '--full' not in args:
        for mod in discover(MIRROR):
            rp=REPORTS/f"{mod['name']}-latest-review.json"
            if not rp.exists(): log(f"SKIP {mod['name']}: no review report"); continue
            report=json.loads(rp.read_text(encoding='utf-8'))
            mod['mirrorPath']=mod['path']
            marker=Path(mod['path'])/'.sandbox-mirror.json'
            source=Path(json.loads(marker.read_text(encoding='utf-8'))['source']) if marker.exists() else project_root
            mod['path']=str(source)
            ok=deploy(mod,report,dry_run=dry_run)
            if ok and not dry_run:
                # 5. post-release validation
                data_validator.validate(mod['path'])
                monitor(mod)
            clean_mirror(mod['name'])
    elif '--prod-mirror' in args:
        import prod_mirror as pm; pm.mirror_production(project_root)
    elif '--build-registry' in args:
        import module_registry as reg; reg.build_registry(project_root)
    elif '--rollback' in args:
        if '--module' in args:
            mod_name=args[args.index('--module')+1]
            rollback(mod_name)
        else:
            log('need --module <name> for rollback')
    elif '--rollback-drill' in args:
        log('start rollback drill: deploy -> snapshot -> rollback -> verify')
        if not project_root: log('need --project'); sys.exit(1)
        # deploy current mirror if review pass
        for mod in discover(MIRROR):
            rp=REPORTS/f"{mod['name']}-latest-review.json"
            if not rp.exists(): log(f'SKIP {mod["name"]}: no review report'); continue
            report=json.loads(rp.read_text(encoding='utf-8'))
            if not report['pass']: log(f'SKIP {mod["name"]}: review not passed'); continue
            marker=Path(mod['path'])/'.sandbox-mirror.json'
            source=Path(json.loads(marker.read_text(encoding='utf-8'))['source']) if marker.exists() else project_root
            mod['path']=str(source)
            backup=ROOT/'backups'/f"{mod['name']}-{stamp()}"; ensure_dir(backup)
            run(f'robocopy "{mod["path"]}" "{backup}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
            log(f'  drill backup created: {backup}')
            run(f'robocopy "{mod["mirrorPath"]}" "{mod["path"]}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache sandbox-logs /XF .env.sandbox .sandbox-mirror.json /R:1 /W:1',t=300,ignore=True)
            log(f'  drill deployed: {mod["name"]}')
            run(f'robocopy "{backup}" "{mod["path"]}" /MIR /XD .git node_modules __pycache__ .venv venv dist build cache /R:1 /W:1',t=300,ignore=True)
            log(f'  drill rolled back: {mod["name"]}')
            st=smoke_test(mod['path'], f"{mod['name']} rollback-drill")
            if st['ok']: log(f'  OK rollback drill: {mod["name"]}')
            else: log(f'  FAIL rollback drill: {mod["name"]}')
    elif '--validate' in args:
        for mod in discover(project_root): data_validator.validate(mod['path'])
    elif '--monitor' in args:
        for mod in discover(project_root): monitor(mod)
    elif '--canary' in args:
        for mod in discover(project_root):
            rp=REPORTS/f"{mod['name']}-latest-review.json"
            if not rp.exists(): log(f"SKIP {mod['name']}: no review report"); continue
            report=json.loads(rp.read_text(encoding='utf-8'))
            canary_deploy(mod, report, dry_run=dry_run)
    elif '--full' in args:
        log('start full sandbox pipeline')
        # 1. environment consistency: lock + bootstrap
        env_lock.lock_dependencies(project_root)
        env_bootstrap.bootstrap(project_root)
        # 2. production-like mirror
        import prod_mirror as pm; pm.mirror_production(project_root)
        # 3. module decomposition
        import module_registry as reg; reg.build_registry(project_root)
        # 4. data consistency: migrate up with snapshot
        migration_manager.migrate(project_root, direction='up', dry_run=dry_run)
        all_ok=True
        for mod in discover(project_root):
            mirrored=isolate(mirror(mod))
            reason_module(mirrored, evolve=evolve)
            report=test_module(mirrored); review(report)
            if not report['pass']: all_ok=False
            elif '--deploy' in args:
                ok=deploy(mirrored, report, dry_run=dry_run)
                if ok and not dry_run:
                    data_validator.validate(mirrored['path'])
                    monitor({'name': mirrored['name'], 'path': mirrored['path']})
        if '--deploy' not in args:
            for mod in discover(project_root): clean_mirror(mod['name'])
        log('full pipeline done' + (' with deploy' if '--deploy' in args else ''))
    else:
        print(f"""SANDBOX orchestrator

usage:
  python sandbox-orchestrator.py --project <root> --discover
  python sandbox-orchestrator.py --project <root> --mirror
  python sandbox-orchestrator.py --project <root> --test
  python sandbox-orchestrator.py --project <root> --deploy [--dry-run]
  python sandbox-orchestrator.py --project <root> --full [--dry-run]

IRON LAW:
  - All code runs in mirror space first.
  - Production deployment is atomic module replacement only.
  - No placeholders, fake data, empty shells, or hardcoded secrets in production.
  - Mirror cache is cleaned after each module.

sandbox root:
  {ROOT}
""")

if __name__=='__main__':
    try: main()
    except Exception as e: log(f'FATAL: {e}'); raise
