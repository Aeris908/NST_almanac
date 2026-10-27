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
    if str(s_id) in ['2', '3', '4', '5', '6', '7']:
        matches = [m for m in s.get('matches', []) if any(k in (m.get('tour','') + m.get('league','')).lower() for k in ['финал', '1/', 'плей', 'playoff', 'кубок'])]
        print(f"\n================ SEASON {s_id}: {s.get('name')} ================")
        print(f"Total playoff matches: {len(matches)}")
        for idx, m in enumerate(matches[:8]):
            print(f"[{idx+1}] p1: {m.get('p1')} vs p2: {m.get('p2')} | score: {m.get('s1')}:{m.get('s2')} | tour: '{m.get('tour')}' | league: '{m.get('league')}'")
            print(f"     vk_text snippet: {repr(m.get('vk_text', '')[:120])}")
