import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

url = f"https://api.vk.ru/method/board.getTopics?group_id={group_id}&count=100&access_token={token}&v=5.199"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    items = resp.get('response', {}).get('items', [])
    print(f"Total topics found: {len(items)}")
    for t in items:
        title = t.get('title', '')
        t_id = t.get('id')
        comments = t.get('comments', 0)
        print(f"  [ID: {t_id}] ({comments} comments) {title}")
except Exception as e:
    print("Error:", e)
