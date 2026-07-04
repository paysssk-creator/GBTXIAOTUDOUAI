"""临时分析脚本：扫描 _script_init.html 内的 function 边界"""
from pathlib import Path
import re
p = Path('desktop/templates/partials/_script_init.html')
t = p.read_text(encoding='utf-8')
lines = t.splitlines(keepends=False)
print('total lines:', len(lines))
fns = []
for i, line in enumerate(lines, 1):
    m = re.match(r'^\s*function\s+(\w+)\s*\(', line)
    if m:
        start = i
        depth = 0
        seen_open = False
        for j in range(i - 1, len(lines)):
            for k, ch in enumerate(lines[j]):
                if ch == '{':
                    depth += 1
                    seen_open = True
                elif ch == '}':
                    depth -= 1
            if seen_open and depth == 0:
                fns.append((m.group(1), start, j + 1))
                break
for n, s, e in fns:
    print(f'  L{s:4d}..{e:4d} ({e-s+1:3d} lines) function {n}')
print('total funcs in _script_init:', len(fns))
print('sum function bodies:', sum(e - s + 1 for _, s, e in fns))
