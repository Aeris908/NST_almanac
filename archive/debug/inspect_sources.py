import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_final_analytics.py', encoding='utf-8') as f:
    text = f.read()

import re
# Find sections for Season 5, 6, 7, 2, 3
for m in re.finditer(r'#.*Season [23567].*', text):
    start = m.start()
    print(text[start:start+400])
    print('='*50)
