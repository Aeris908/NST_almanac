import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

# Search wall with wall.search
queries = ['молодёж', 'молодеж', 'межсезон', 'сольный', 'блиц-турнир', 'кубок лиг', 'пенальти']
found_posts = {}

for q in queries:
    url = f"https://api.vk.ru/method/wall.search?owner_id=-{group_id}&query={urllib.parse.quote(q)}&count=100&access_token={token}&v=5.199"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        for post in items:
            pid = post['id']
            if pid not in found_posts:
                found_posts[pid] = post
    except Exception as e:
        print(f"Error searching '{q}': {e}")

print(f"Total matching wall posts found: {len(found_posts)}")

for pid, post in sorted(found_posts.items(), key=lambda x: x[1].get('date', 0), reverse=True):
    text = post.get('text', '').replace('\n', ' ')[:100]
    links = re.findall(r'(https?://[^\s]+|page-[0-9_]+|topic-[0-9_]+)', post.get('text', ''))
    print(f"  Post {pid} (likes: {post.get('likes', {}).get('count', 0)}): {text}")
    if links:
        print(f"    Links: {links[:3]}")
