import urllib.request, json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

topics_to_check = {
    "Season 2": 33103100,
    "Season 3": 33967365,
    "Season 4": 34973011,
    "Season 5": 36630593,
    "Season 6": 39660451,
    "Season 7": 49054760,
}

for s_name, tid in topics_to_check.items():
    url = f"https://api.vk.ru/method/board.getComments?group_id={group_id}&topic_id={tid}&count=10&access_token={token}&v=5.199"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    items = resp.get('response', {}).get('items', [])
    total_count = resp.get('response', {}).get('count', 0)
    print(f"\n{'='*60}\n{s_name} (Topic ID: {tid}, Total Comments: {total_count})\n{'='*60}")
    if items:
        first_post = items[0].get('text', '')
        print("First Post (Summary/Rules/Links):")
        print(first_post[:400])
        # Find Google Sheet links or Challonge links
        links = re.findall(r'https?://[^\s<>"]+', first_post)
        print("Links in first post:", links)
