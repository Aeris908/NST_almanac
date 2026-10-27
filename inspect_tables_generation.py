import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '.tables' in l or "['tables']" in l or '\"tables\":' in l or "'tables':" in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
