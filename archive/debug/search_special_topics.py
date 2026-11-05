import json, re, sys

sys.stdout.reconfigure(encoding='utf-8')
topics = json.load(open('all_group_topics.json', encoding='utf-8'))
for t in topics:
    title = t.get('title', '')
    if any(k in title.lower() for k in ['молод', 'юниор', 'кубок', 'блиц', 'пенальт', 'сольн', 'межсез', 'клубн']):
        print(f"Topic {t.get('id')}: {title} (comments: {t.get('comments')})")
