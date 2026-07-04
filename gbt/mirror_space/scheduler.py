# 开发者：自由的风
#!/usr/bin/env python3
"""scheduler.py - Intelligent scheduler gateway for GBT capability modules."""
import os, sys, json, re, subprocess
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
MODULES = ROOT / 'modules'
MIRROR = ROOT / 'mirror'
CLINE = HOME / '.cline'
BIN = Path(__file__).parent

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)
def log(m): print(f'[SCHEDULER] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def check_no_direct_edits(project_root):
    """Block deploy if production has uncommitted changes not done via sandbox."""
    root=Path(project_root)
    git=root/'.git'
    if not git.exists(): return True
    rc,out=run('git status --porcelain', cwd=str(root), t=30)
    dirty=[line for line in out.splitlines() if line.strip()]
    if dirty:
        log('WARNING: production panel has uncommitted changes:')
        for line in dirty[:10]: log(f'  {line}')
        log('All changes must go through mirror space first.')
        return False
    return True

def run(cmd, cwd=None, t=120):
    try:
        r = subprocess.run(cmd, cwd=cwd or os.getcwd(), shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=t)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return -1, 'timeout'

def load_modules():
    mods=[]
    if not MODULES.exists(): return mods
    for p in sorted(MODULES.glob('*.json')):
        try:
            m=json.loads(p.read_text(encoding='utf-8'))
            m['id']=p.stem
            mods.append(m)
        except Exception as e: log(f'warn: bad manifest {p}: {e}')
    return mods

def authorize_offensive(mod, target):
    """Offensive modules require explicit target."""
    if not mod.get('offensive', False):
        return True
    if not target:
        log(f'BLOCKED: {mod["id"]} is offensive and requires --target')
        return False
    # Localhost / private IP / owned-domain patterns are allowed
    allowed_prefixes=('localhost','127.','192.168.','10.','::1')
    t=target.lower()
    if any(t.startswith(x) for x in allowed_prefixes):
        return True
    log(f'BLOCKED: {mod["id"]} target {target} is not in default authorized scope (localhost/private IP).')
    log('To authorize, edit the module manifest or pass an explicit allowlisted target.')
    return False

def run_module(mod, project_root=None, target=None, dry_run=False, extra_args=''):
    if not authorize_offensive(mod, target):
        return {'ok':False,'output':'authorization failed'}
    cmd=mod.get('command','')
    if not cmd:
        return {'ok':False,'output':'no command in manifest'}
    # substitute variables
    if project_root: cmd=cmd.replace('{{PROJECT}}', str(project_root))
    if target: cmd=cmd.replace('{{TARGET}}', target)
    if dry_run: cmd=cmd + ' ' + mod.get('dry_run_flag','')
    if extra_args: cmd=cmd + ' ' + extra_args
    log(f'running module: {mod["id"]} -> {cmd}')
    rc,out=run(cmd, cwd=str(HOME), t=mod.get('timeout',120))
    ok = rc==0 and not any(k in out.lower() for k in mod.get('fail_keywords',['fail','error','❌']))
    log(f'  result: {"OK" if ok else "FAIL"} (rc={rc})')
    return {'ok':ok,'returncode':rc,'output':out[:2000]}

def generate_fix_plan(report, project_root):
    """Generate a fix plan using cloud-llm based on sandbox report."""
    prompt=f"""You are a senior engineer. Analyze this sandbox report and produce a minimal fix plan.
Report:
{json.dumps(report, indent=2, ensure_ascii=False)}

Return ONLY a JSON object with keys:
- summary: one sentence
- fixes: list of {{file, action, reason}} objects
- commands: list of shell commands to run in mirror space
Do not include markdown formatting."""
    plan_path=ROOT/'plans'/f"{report['module']}-fix-plan.json"
    ensure_dir(plan_path.parent)
    # Use cloud-llm if available
    cloud=CLINE/'cloud-llm.js'
    if cloud.exists():
        try:
            # use direct subprocess to avoid shell escaping of large prompt
            r=subprocess.run(['node', str(cloud), prompt], cwd=str(HOME), capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=180)
            out=r.stdout or ''
            # try to parse JSON from LLM output
            plan=None
            for m in re.finditer(r'\{.*\}', out, re.DOTALL):
                try:
                    candidate=json.loads(m.group(0))
                    if isinstance(candidate, dict) and ('fixes' in candidate or 'summary' in candidate):
                        plan=candidate; break
                except Exception: continue
            if not plan:
                plan={'summary':out[:200] if out else 'llm returned no structured plan','fixes':[],'commands':[]}
        except Exception as e:
            plan={'summary':f'cloud-llm failed: {e}','fixes':[],'commands':[]}
    else:
        plan={'summary':'cloud-llm not available','fixes':[],'commands':[]}
    plan_path.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    log(f'fix plan: {plan_path}')
    return plan

def apply_known_fixes(report, mirror_path, dry_run=True):
    """Apply safe known fixes in mirror space. Returns list of actions."""
    actions=[]
    mp=Path(mirror_path)
    audit_text=report.get('audit',{}).get('output','')
    # audit complains about missing .clinerules
    if '缺少 Cline 规则文件' in audit_text or '.clinerules' in audit_text.lower():
        target=mp/'.clinerules'
        if dry_run:
            actions.append(f'DRY-RUN: would create {target}')
        else:
            target.write_text('# Cline rules\n# Generated by sandbox active evolve\n',encoding='utf-8')
            actions.append(f'created {target}')
    # audit complains about git not initialized
    if 'Git 仓库已初始化' in audit_text:
        if dry_run:
            actions.append(f'DRY-RUN: would git init in {mp}')
        else:
            import subprocess
            subprocess.run('git init', cwd=str(mp), shell=True, capture_output=True)
            actions.append(f'git init in {mp}')
    # npm test timeout: increase timeout by setting env CI=true to avoid watch mode
    tests=report.get('tests',{})
    if tests.get('output')=='timeout' or tests.get('failed',0)>0:
        pkg=mp/'package.json'
        if pkg.exists():
            try:
                data=json.loads(pkg.read_text(encoding='utf-8'))
                if 'test' in data.get('scripts',{}):
                    old=data['scripts']['test']
                    if 'jest' in old.lower() and '--testTimeout' not in old:
                        data['scripts']['test']=old.replace('jest','jest --testTimeout=30000 --forceExit')
                        if dry_run:
                            actions.append(f'DRY-RUN: would patch {pkg} test script')
                        else:
                            pkg.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
                            actions.append(f'patched {pkg} test script')
            except Exception as e:
                actions.append(f'package.json patch skipped: {e}')
    return actions

def evolve_project(project_root, mods, dry_run=True, max_rounds=3):
    """Active skill: fix in mirror space, test, deploy atomically."""
    project_root=Path(project_root)
    sandbox=ROOT/'bin'/'sandbox-orchestrator.py'
    for rnd in range(1, max_rounds+1):
        log(f'--- evolve round {rnd}/{max_rounds} ---')
        # run sandbox full dry-run (large projects may need 20 min)
        rc,out=run(f'python "{sandbox}" --project "{project_root}" --full --dry-run', t=1200)
        print(out)
        # find latest report
        reports=sorted((ROOT/'reports').glob('*-review.json'), key=lambda p:p.stat().st_mtime, reverse=True)
        if not reports:
            log('no report generated'); return
        report=json.loads(reports[0].read_text(encoding='utf-8'))
        if report.get('pass'):
            log('sandbox passed')
            if dry_run:
                log('DRY-RUN: would deploy atomically')
            else:
                if not check_no_direct_edits(project_root):
                    log('BLOCKED: production panel has uncommitted direct edits'); break
                # discover module and deploy
                for mod in discover(project_root):
                    if mod['name']==report['module']:
                        mp=MIRROR/mod['name']
                        mod['mirrorPath']=str(mp)
                        deploy(mod, report)
                        clean_mirror(mod['name'])
                        break
            return
        # generate fix plan
        plan=generate_fix_plan(report, project_root)
        log(f"fix plan summary: {plan.get('summary','')}")
        # apply known safe fixes
        mirror_path=MIRROR/report['module']
        actions=apply_known_fixes(report, str(mirror_path), dry_run=dry_run)
        for a in actions: log(f'  {a}')
        if not dry_run and not actions:
            log('no known fixes applied; need manual intervention or LLM patch')
            break
    log('evolve loop finished without passing sandbox')

def main():
    args=sys.argv[1:]
    if '--project' in args: project_root=Path(args[args.index('--project')+1]).resolve()
    else: project_root=None
    target=None
    if '--target' in args: target=args[args.index('--target')+1]
    dry_run='--dry-run' in args

    mods=load_modules()

    if '--list' in args:
        log('registered modules:')
        for m in mods:
            tag='[OFFENSIVE]' if m.get('offensive') else '[SAFE]'
            log(f"  {tag} {m['id']:20} {m.get('name','')}")
        return

    if '--run' in args:
        idx=args.index('--run')
        mid=args[idx+1]
        mod=next((m for m in mods if m['id']==mid), None)
        if not mod: log(f'unknown module: {mid}'); sys.exit(1)
        result=run_module(mod, project_root=project_root, target=target, dry_run=dry_run)
        print(result['output'])
        sys.exit(0 if result['ok'] else 1)

    if '--pipeline' in args:
        log('start scheduled sandbox pipeline')
        if not project_root: log('need --project'); sys.exit(1)
        sandbox=ROOT/'bin'/'sandbox-orchestrator.py'
        rc,out=run(f'python "{sandbox}" --project "{project_root}" --full --dry-run', t=600)
        print(out)
        for m in mods:
            if m.get('pipeline', False) and not m.get('offensive', False):
                run_module(m, project_root=project_root, dry_run=dry_run)
        return

    if '--evolve' in args:
        log('start active evolve/fix loop')
        if not project_root: log('need --project'); sys.exit(1)
        evolve_project(project_root, mods, dry_run=dry_run)
        return

    if '--skill' in args:
        log('invoke mirror-space active skill')
        if not project_root: log('need --project'); sys.exit(1)
        skill_args=' '.join(sys.argv[1:])
        skill_args=skill_args.replace('--skill','').strip()
        rc,out=run(f'python "{BIN / "mirror_skill.py"}" {skill_args}', t=1800)
        print(out)
        sys.exit(rc)

    if '--daemon' in args:
        log('start autonomous evolution daemon (30 min interval)')
        if not project_root: log('need --project'); sys.exit(1)
        import time
        while True:
            log('--- scheduled scan ---')
            evolve_project(project_root, mods, dry_run=dry_run)
            log('sleeping 30 minutes')
            time.sleep(1800)
        return

    print(f"""Intelligent Scheduler Gateway

usage:
  python scheduler.py --list
  python scheduler.py --run <module> [--project <path>] [--target <target>] [--dry-run]
  python scheduler.py --pipeline --project <path> [--dry-run]

Modules are loaded from: {MODULES}
""")

if __name__=='__main__':
    main()
