import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')
token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'

queries = [
    "V Командный Чемпионат по Goal 3. Занавес",
    "Итак Командный Гол 3 завершился и вот он финальный пост",
    "Волею судеб именно вчера, 22.09.2015"
]

for q in queries:
    url = f"https://api.vk.ru/method/wall.search?owner_id=-66162180&query={urllib.parse.quote(q)}&count=5&access_token={token}&v=5.199"
    try:
        resp = json.loads(urllib.request.urlopen(url, timeout=10).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        for item in items:
            print("="*40)
            print("QUERY:", q)
            print(item.get('text'))
    except Exception as e:
        print("ERR:", e)
