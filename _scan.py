"""Deep scan: syntax, security, imports"""
import os, sys, ast, re, subprocess

BASE = r"C:\Users\ADMIN\GBTXIAOTUDOUAI"
os.chdir(BASE)

def p(text):
    """Safe print avoiding GBK encoding issues"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))

p("=" * 60)
p("  GBTXIAOTUDOUAI - Deep Scan")
p("=" * 60)

# 1. Python syntax check
p("\n[1] Python syntax check...")
bad = []
count = 0
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__", ".gbt", "node_modules")]
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            count += 1
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    ast.parse(fh.read())
            except SyntaxError as e:
                bad.append(f"{os.path.relpath(fp, BASE)}: {e}")
            except:
                pass

p(f"   Files checked: {count}, Syntax errors: {len(bad)}")
for b in bad:
    p(f"   [FAIL] {b}")

# 2. Security scan
p("\n[2] Security scan (hardcoded credentials)...")
SECRET_PATTERNS = [
    (r'(?i)api[_]?key\s*=\s*["\'][\w\-]{10,}["\']', "API_KEY"),
    (r'(?i)token\s*=\s*["\'][\w\-\.]{15,}["\']', "TOKEN"),
    (r'(?i)password\s*=\s*["\'][^"\']+["\']', "PASSWORD"),
    (r'(?i)secret\s*=\s*["\'][^"\']+["\']', "SECRET"),
]
secrets_found = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__", ".gbt")]
    for f in files:
        if f.endswith((".py", ".js", ".ts")):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    content = fh.read()
                for pat, label in SECRET_PATTERNS:
                    if re.search(pat, content) and ".env.example" not in fp and "test_" not in fp:
                        secrets_found.append(f"{os.path.relpath(fp, BASE)}: {label}")
            except:
                pass
p(f"   Hardcoded credentials: {len(secrets_found)}")
for s in secrets_found:
    p(f"   [WARN] {s}")

# 3. Debugger check
p("\n[3] Debugger check...")
debug_found = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__", ".gbt")]
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    content = fh.read()
                if "breakpoint()" in content:
                    debug_found.append(f"{os.path.relpath(fp, BASE)}")
                if "pdb.set_trace()" in content:
                    debug_found.append(f"{os.path.relpath(fp, BASE)}")
            except:
                pass
p(f"   Debugger statements: {len(debug_found)}")
for d in debug_found:
    p(f"   [WARN] {d}")

# 4. Import check
p("\n[4] Critical import check...")
IMPORTS = [
    ("flask", "Flask,render_template_string,jsonify,request"),
    ("psutil", ""),
    ("json", ""),
    ("tkinter", ""),
    ("threading", ""),
    ("subprocess", ""),
    ("urllib.request", ""),
]
for mod, names in IMPORTS:
    try:
        if names:
            exec(f"from {mod} import {names}")
        else:
            exec(f"import {mod}")
        p(f"   [OK] {mod}")
    except Exception as e:
        p(f"   [MISS] {mod}: {e}")

# 5. Installed vs requirements
p("\n[5] Installed packages vs requirements.txt...")
try:
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=15)
    installed = set()
    for line in result.stdout.split("\n"):
        line = line.strip().lower()
        if "==" in line:
            installed.add(line.split("==")[0])

    req_path = os.path.join(BASE, "requirements.txt")
    missing = []
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkg = line.split(">=")[0].split("<")[0].split("=")[0].strip().lower()
                if pkg not in installed:
                    missing.append(pkg)
    p(f"   Missing packages: {len(missing)}")
    for m in missing:
        p(f"   [MISS] {m}")
except Exception as e:
    p(f"   [ERR] pip check failed: {e}")

# 6. .gitignore check
p("\n[6] .gitignore coverage check...")
gipath = os.path.join(BASE, ".gitignore")
ignored_patterns = []
if os.path.exists(gipath):
    with open(gipath, "r", encoding="utf-8") as f:
        ignored_patterns = [l.strip() for l in f if l.strip() and not l.startswith("#")]

disk_files = set()
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__", ".gbt")]
    for f in files:
        disk_files.add(f)

git_tracked = set(subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=BASE).stdout.strip().split("\n"))

should_be_ignored = {"BOUNTY_REPORT_", "AUDIT_REPORT.json", "AUTO_FIX_PLAN.json", 
                     "VULN-FINDINGS.json", "VULN-FINDINGS.md", "paper_account.json",
                     ".cline-memory.md", ".clinerules", "store.json"}

leaked = []
for gf in git_tracked:
    gf_base = os.path.basename(gf)
    for pat in should_be_ignored:
        if pat in gf or gf_base == pat:
            if not any(gf.startswith(ip.replace("*","").rstrip("/")) for ip in ignored_patterns if ip):
                leaked.append(gf)
p(f"   Tracked files that should be ignored: {len(leaked)}")
for l in leaked:
    p(f"   [LEAK] {l}")

# Summary
p("\n" + "=" * 60)
p(f"SUMMARY: syntax={len(bad)} secrets={len(secrets_found)} debug={len(debug_found)} missing={len(missing)} leaks={len(leaked)}")
p("=" * 60)

