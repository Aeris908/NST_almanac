import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('build_final_analytics.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'Season 8' in l or 'Season 9' in l or 'Дворовая' in l or 'Средняя' in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
