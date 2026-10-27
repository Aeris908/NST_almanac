import urllib.request, json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

# Topic 49054760 is Season 7 (212 comments)
url = f"https://api.vk.ru/method/board.getComments?group_id={group_id}&topic_id=49054760&count=40&offset=30&access_token={token}&v=5.199"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
items = resp.get('response', {}).get('items', [])

print(f"Comments fetched from Season 7: {len(items)}")
score_pattern = re.compile(r'(\d+)\s*[:\-]\s*(\d+)')
for c in items:
    text = c.get('text', '').replace('\n', ' ')
    if score_pattern.search(text):
        print(f"[{c['id']}] {text}")
