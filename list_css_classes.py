import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('<style>')
idx2 = text.find('</style>')
css_text = text[idx1:idx2]

# Let's see all class names in CSS
import re
classes = set(re.findall(r'\.([a-zA-Z0-9_-]+)', css_text))
print("Total classes in CSS:", len(classes))
print("Sample classes:", sorted(list(classes))[:40])
