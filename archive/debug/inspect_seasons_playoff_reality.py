import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('deploy/soccer.html', encoding='utf-8') as f:
    text = f.read()

prefix = 'const DATA = '
start = text.find(prefix) + len(prefix)
end = text.find(';\n', start)
data = json.loads(text[start:end])

for s in data['seasons']:
    s_id = s.get('id')
    cup_matches = [m for m in s.get('matches', []) if any(k in (m.get('tour','')+m.get('league','')).lower() for k in ['финал', '1/', 'плей', 'playoff', 'кубок'])]
    print(f"Season {s_id} ({s.get('name')}, {s.get('year')}): {len(cup_matches)} playoff matches")
    for m in cup_matches[:4]:
        vk = repr(m.get('vk_text', ''))[:50]
        print(f"   {m.get('p1')} vs {m.get('p2')} ({m.get('s1')}:{m.get('s2')}) | tour: '{m.get('tour')}' | league: '{m.get('league')}' | vk: {vk}")
