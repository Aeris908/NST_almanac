import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'specialTournamentDetailContainer', text)]
for idx in matches:
    print(text[idx-100:idx+400])
    print("=" * 60)
