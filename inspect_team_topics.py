import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')
token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'

topics = [
    (49868493, "VI Командный Чемпионат"),
    (35995200, "V Командный Чемпионат"),
    (33672355, "IV Командный Чемпионат"),
    (31898219, "Летний командный турнир 2015"),
]

for t_id, name in topics:
    print(f"\n==================== {name} (Topic {t_id}) ====================")
    url = f"https://api.vk.ru/method/board.getComments?group_id=66162180&topic_id={t_id}&count=10&access_token={token}&v=5.199"
    try:
        resp = json.loads(urllib.request.urlopen(url, timeout=10).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        for c in items[:3]:
            txt = c.get('text', '')
            print("--- COMMENT ---")
            print(txt[:600])
            for att in c.get('attachments', []):
                print("   ATT:", att.get('type'))
    except Exception as e:
        print("ERR:", e)
