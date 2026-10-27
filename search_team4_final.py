import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')
token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'

url = f"https://api.vk.ru/method/wall.search?owner_id=-66162180&query={urllib.parse.quote('ФИНАЛ КОМАНДНОГО ЧЕМПИОНАТА')}&count=20&access_token={token}&v=5.199"
try:
    resp = json.loads(urllib.request.urlopen(url, timeout=10).read().decode('utf-8'))
    for item in resp.get('response', {}).get('items', []):
        print("WALL POST:", item.get('text')[:300])
except Exception as e:
    print("ERR:", e)
