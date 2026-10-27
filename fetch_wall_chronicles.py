import urllib.request, urllib.parse, json, sys, re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

# Let's search wall posts for key tournament recaps & announcements
keywords = [
    '1 сольный', '2 сольный', '3 сольный', '4 сольный', '5 сольный', '6 сольный', '7 сольный', '8 сольный', '9 сольный',
    'итоги сезона', 'чемпионат по гол3', 'soccer league', 'командный чемпионат', 'кубок лиг', 'финал кубка',
    'кубок давителя', 'турнир по пенальти', 'блиц-турнир', 'летопись'
]

wall_results = {}

for kw in keywords:
    try:
        url = f"https://api.vk.ru/method/wall.search?owner_id=-{group_id}&query={urllib.parse.quote(kw)}&count=40&access_token={token}&v=5.199"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
        items = res.get('response', {}).get('items', [])
        for post in items:
            pid = post['id']
            if pid not in wall_results:
                wall_results[pid] = {
                    'id': pid,
                    'date': post.get('date'),
                    'text': post.get('text', ''),
                    'likes': post.get('likes', {}).get('count', 0),
                    'attachments': [a.get('type') for a in post.get('attachments', [])]
                }
    except Exception as e:
        print(f"Error on {kw}: {e}")

print(f"Fetched {len(wall_results)} wall posts relevant to tournaments.")

# Save to scratch for analysis
with open('wall_tournaments_posts.json', 'w', encoding='utf-8') as f:
    json.dump(wall_results, f, ensure_ascii=False, indent=2)

print("Saved wall_tournaments_posts.json")
