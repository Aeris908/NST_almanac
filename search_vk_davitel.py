import urllib.request, json, sys, urllib.parse

sys.stdout.reconfigure(encoding='utf-8')
token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'

print("=== SEARCHING WALL POSTS FOR DAVITEL / ДАВИТЕЛЬ ===")
for q in ["Davitel", "Давитель"]:
    url = f"https://api.vk.ru/method/wall.search?owner_id=-66162180&query={urllib.parse.quote(q)}&count=50&access_token={token}&v=5.199"
    try:
        resp = json.loads(urllib.request.urlopen(url, timeout=10).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        print(f"Query '{q}': found {len(items)} wall posts")
        for item in items[:10]:
            print(f"  [ID {item.get('id')}] {item.get('text')[:160].replace(chr(10), ' ')}")
    except Exception as e:
        print("ERR:", e)
