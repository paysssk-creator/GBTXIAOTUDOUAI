# 开发者：自由的风\n#!/usr/bin/env python3
"""mirror-reasoner.py - Architecture reasoning for mirror space.
Defaults to cloud-llm (Kimi) for fast inference.
Set USE_LOCAL=True to use local Ollama 7B (much slower on CPU).
"""
import os, sys, json, re, subprocess, requests
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME'))
ROOT = HOME / '.gbt' / 'sandbox'
CLINE = HOME / '.cline'
USE_LOCAL = os.environ.get('REASONER_LOCAL','false').lower()=='true'
LOCAL_MODEL = 'qwen2.5-coder:7b'
OLLAMA = 'http://localhost:11434'

def log(m): print(f'[REASONER] {datetime.now().strftime("%H:%M:%S")} {m}', flush=True)

def load_moonshot_key():
    try:
        pf=CLINE/'data'/'settings'/'providers.json'
        if pf.exists():
            data=json.loads(pf.read_text(encoding='utf-8'))
            for v in data.get('providers',{}).values():
                k=v.get('settings',{}).get('apiKey','')
                if k and 'moonshot' in v.get('api','').lower(): return k
                if k and 'moonshot' in str(v).lower(): return k
    except Exception: pass
    return os.environ.get('MOONSHOT_API_KEY','')

def cloud_generate(prompt):
    """Call Kimi Moonshot API directly for fast reasoning."""
    key=load_moonshot_key()
    if not key:
        log('Moonshot API key not found'); return None
    try:
        r=requests.post('https://api.moonshot.cn/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model':'moonshot-v1-8k','messages':[{'role':'user','content':prompt}],
                  'temperature':0.2,'max_tokens':600},
            timeout=120)
        r.raise_for_status()
        out=r.json()['choices'][0]['message']['content']
        m=re.search(r'\{.*\}', out, re.DOTALL)
        return m.group(0) if m else out
    except Exception as e:
        log(f'cloud-llm failed: {e}')
        return None

def ollama_generate(prompt, model=LOCAL_MODEL, temperature=0.2):
    """Call local Ollama. Slow on CPU, use with care."""
    try:
        r = requests.post(f'{OLLAMA}/api/generate', json={
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': temperature, 'num_ctx': 4096, 'num_predict': 600}
        }, timeout=600)
        r.raise_for_status()
        return r.json().get('response','')
    except Exception as e:
        log(f'ollama error: {e}')
        return None

def generate(prompt):
    if USE_LOCAL:
        return ollama_generate(prompt)
    return cloud_generate(prompt)

def summarize_project(path, max_files=40):
    """Collect file tree for architecture analysis."""
    files=[]
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {'node_modules','.git','__pycache__','.venv','venv','dist','build','vendor','.claude','.github','.husky','sandbox','.gbt'}]
        for fn in filenames:
            if fn.endswith(('.ts','.js','.tsx','.jsx','.py','.go','.rs','.java','.json','.md')) and not fn.endswith(('.test.ts','.spec.ts','.test.js','.spec.js')):
                fp=Path(root)/fn
                files.append(str(fp.relative_to(path)))
            if len(files)>=max_files: break
        if len(files)>=max_files: break
    return files

def score_architecture(project_path, module_name):
    files=summarize_project(project_path)
    if not files:
        return None
    files_text='\n'.join(['- '+f for f in files])
    prompt=f"""You are an expert software architect. Analyze the architecture of project '{module_name}'.

File tree:
{files_text}

Return ONLY a JSON object with this structure:
{{
  "current_score": 0-100,
  "proposed_score": 0-100,
  "reasoning": "brief analysis",
  "recommendations": ["list of concrete improvements"],
  "safe_to_apply": true/false
}}

Score based on: modularity, separation of concerns, testability, security, maintainability, performance.
Only set safe_to_apply=true if the proposed changes are low-risk refactorings that do not change external behavior.
"""
    log(f'analyzing architecture of {module_name} with {"local 7B" if USE_LOCAL else "Kimi cloud"}...')
    resp=generate(prompt)
    if not resp:
        log('reasoning failed'); return None
    try:
        m=re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            result=json.loads(m.group(0))
            log(f"current score: {result.get('current_score')}, proposed: {result.get('proposed_score')}")
            return result
    except Exception as e:
        log(f'failed to parse reasoning result: {e}')
        log(resp[:300])
    return None

def generate_refactor_plan(project_path, module_name, current_score, proposed_score):
    files=summarize_project(project_path, max_files=60)
    files_text='\n'.join(['- '+f for f in files])
    prompt=f"""You are an expert refactor engineer. Project '{module_name}' current architecture score is {current_score}, proposed score is {proposed_score}.

File tree:
{files_text}

Return ONLY a JSON object:
{{
  "actions": [
    {{"file": "relative/path", "operation": "create|modify|delete", "description": "what to do", "code": "full file content or diff snippet"}}
  ]
}}

Only suggest safe refactorings: extract functions, rename variables, add types, simplify logic, improve error handling. Do NOT change APIs or behavior.
"""
    resp=generate(prompt)
    if not resp: return None
    try:
        m=re.search(r'\{.*\}', resp, re.DOTALL)
        if m: return json.loads(m.group(0))
    except Exception as e:
        log(f'failed to parse refactor plan: {e}')
    return None

def apply_actions(project_path, actions, dry_run=True):
    applied=[]
    for a in actions:
        fp=Path(project_path)/a['file']
        op=a.get('operation','modify')
        if dry_run:
            applied.append(f'DRY-RUN {op}: {fp}')
            continue
        ensure_dir(fp.parent)
        if op=='create':
            fp.write_text(a.get('code',''),encoding='utf-8')
            applied.append(f'created {fp}')
        elif op=='modify':
            if not fp.exists():
                applied.append(f'skip modify (not exists): {fp}')
                continue
            fp.write_text(a.get('code',''),encoding='utf-8')
            applied.append(f'modified {fp}')
        elif op=='delete':
            if fp.exists(): fp.unlink()
            applied.append(f'deleted {fp}')
    return applied

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def reason_and_evolve(project_path, module_name, dry_run=True, threshold=5):
    result=score_architecture(project_path, module_name)
    if not result:
        return {'evolved': False, 'reason': 'reasoning failed'}
    cur=result.get('current_score',0)
    prop=result.get('proposed_score',0)
    safe=result.get('safe_to_apply',False)
    if prop - cur < threshold or not safe:
        log(f'no significant improvement ({prop-cur} < {threshold} or unsafe), skipping evolution')
        return {'evolved': False, 'current_score': cur, 'proposed_score': prop, 'reason': 'below threshold or unsafe'}
    plan=generate_refactor_plan(project_path, module_name, cur, prop)
    if not plan or not plan.get('actions'):
        log('no actionable plan generated')
        return {'evolved': False, 'current_score': cur, 'proposed_score': prop, 'reason': 'no plan'}
    log(f"evolving {module_name}: {cur} -> {prop}")
    if dry_run:
        log('dry-run mode: showing planned actions')
    applied=apply_actions(project_path, plan['actions'], dry_run=dry_run)
    for a in applied: log(f'  {a}')
    return {'evolved': True, 'dry_run': dry_run, 'current_score': cur, 'proposed_score': prop, 'actions': applied}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--module', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--local', action='store_true', help='use local Ollama 7B instead of Kimi cloud')
    ap.add_argument('--threshold', type=int, default=5)
    args=ap.parse_args()
    if args.local: USE_LOCAL=True
    r=reason_and_evolve(args.project, args.module, dry_run=args.dry_run, threshold=args.threshold)
    print(json.dumps(r, indent=2, ensure_ascii=False))
