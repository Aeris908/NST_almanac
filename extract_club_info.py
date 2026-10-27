import urllib.request, re, sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for pid in ['53140191', '53171697']:
    req = urllib.request.Request(f'https://vk.com/page-66162180_{pid}', headers=headers)
    html = urllib.request.urlopen(req).read().decode('cp1251', errors='ignore')
    idx = html.find('Пластиковый')
    if idx == -1:
        idx = html.find('Рединский')
    print(f"=== PAGE {pid} ===")
    if idx != -1:
        snippet = html[max(0, idx-200):idx+3000]
        cleaned = re.sub(r'<[^>]+>', ' ', snippet)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        print(cleaned)
    else:
        print("Club name not found directly, finding body...")
        body = re.search(r'<div class="wk_text">(.*?)</div>\s*</div>', html, re.DOTALL)
        if body:
            cleaned = re.sub(r'<[^>]+>', ' ', body.group(1))
            print(re.sub(r'\s+', ' ', cleaned)[:2000])
