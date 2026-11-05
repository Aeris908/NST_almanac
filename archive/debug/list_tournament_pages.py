import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('wiki_inspected.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for k, v in d.items():
    if v['has_tours'] and v['has_scores']:
        # sample text
        print(f"{k} | lines={v['lines_count']} | sample={v['sample_lines'][:3]}")
