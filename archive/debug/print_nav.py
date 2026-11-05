import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2214, 2250):
    print(f"{i+1}: {lines[i]}", end='')
