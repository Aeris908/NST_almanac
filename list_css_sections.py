import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('<style>')
idx2 = text.find('</style>')
css_text = text[idx1:idx2]

# Let's see major comments / sections in CSS
import re
comments = re.findall(r'/\*.*?\*/', css_text, re.DOTALL)
for c in comments:
    print(c.strip())
