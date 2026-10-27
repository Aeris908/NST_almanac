import re, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("build_nekketsu_portal_v2.py", "r", encoding="utf-8") as f:
    code = f.read()

for tid in ["tab-seasons", "tab-teams", "tab-special"]:
    m = re.search(r'<section id="' + tid + r'".*?</section>', code, re.DOTALL)
    print(f"Section {tid}: {len(m.group(0)) if m else 0} chars")

for fn in ["renderSeasonsBar", "renderSeasonDetails", "renderTeamTournaments", "renderSpecialTournaments"]:
    m = re.search(r'function ' + fn + r'\b', code)
    print(f"Function {fn}: {'found' if m else 'NOT found'}")
