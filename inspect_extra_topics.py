import urllib.request, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

topic_ids = [
    (41270759, "2-й Молодёжный Чемпионат по Goal 3"),
    (39731903, "Клубный Чемпионат по Goal 4. МЕЖСЕЗОНЬЕ"),
    (47607364, "Сольный рейтинг по Goal 4"),
    (34920573, "4-й сольный турнир по пенальти"),
    (33437511, "3-й сольный турнир по пенальти"),
    (31987256, "2-й сольный турнир по пенальти"),
    (36341322, "X Юбилейный Блиц-турнир"),
    (34840496, "IX Блиц-турнир"),
]

for tid, desc in topic_ids:
    url = f"https://api.vk.ru/method/board.getComments?group_id={group_id}&topic_id={tid}&count=5&access_token={token}&v=5.199"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        print(f"\n==================== [ID: {tid}] {desc} ====================")
        if items:
            first_txt = items[0].get('text', '')
            print("First post snippet:")
            print(first_txt[:400])
            links = re.findall(r'(https?://[^\s]+|page-[0-9_]+)', first_txt)
            if links:
                print("Found links:", links)
    except Exception as e:
        print(f"Error {tid}: {e}")
