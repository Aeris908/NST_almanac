import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

all_topics = []
for offset in range(0, 1000, 100):
    url = f"https://api.vk.ru/method/board.getTopics?group_id={group_id}&count=100&offset={offset}&access_token={token}&v=5.199"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        if not items:
            break
        all_topics.extend(items)
    except Exception as e:
        print(f"Error at offset {offset}: {e}")
        break

print(f"Total topics fetched from group {group_id}: {len(all_topics)}")

# Save all topics to json
with open("all_group_topics.json", "w", encoding="utf-8") as f:
    json.dump(all_topics, f, ensure_ascii=False, indent=2)

keywords = [
    'молодеж', 'молодёж', 'межсезон', 'сольн', 'кубок', 'турнир', 'лиг', 'cup',
    'блиц', 'blitz', 'чемпионат', 'нори', 'одиночн', '1x1', '1х1', '1 на 1',
    'первенство', 'новичк', 'сезон', 'предсезон', 'лето', 'зима', 'весна', 'осень'
]

matching_topics = []
for t in all_topics:
    title = t.get('title', '').lower()
    if any(k in title for k in keywords):
        matching_topics.append(t)

print(f"\nMatching tournament topics found: {len(matching_topics)}")
for t in sorted(matching_topics, key=lambda x: x.get('comments', 0), reverse=True):
    print(f"  [ID: {t['id']}] ({t.get('comments')} комм.) {t['title']}")
