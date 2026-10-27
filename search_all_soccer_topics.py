import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

all_topics = []
for offset in [0, 100, 200, 300, 400, 500]:
    url = f"https://api.vk.ru/method/board.getTopics?group_id={group_id}&count=100&offset={offset}&access_token={token}&v=5.199"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    items = resp.get('response', {}).get('items', [])
    if not items:
        break
    all_topics.extend(items)

print(f"Total topics fetched: {len(all_topics)}")
soccer_topics = []
for t in all_topics:
    title = t.get('title', '')
    if any(k in title.lower() for k in ['goal', 'soccer', 'сольный', 'сезон', 'чемпионат']):
        if any(k in title.lower() for k in ['soccer', 'goal', 'гол', 'футбол']):
            soccer_topics.append(t)

print(f"\nSoccer League topics found ({len(soccer_topics)}):")
for t in soccer_topics:
    print(f"  [ID: {t['id']}] ({t.get('comments')} комм.) {t['title']}")
