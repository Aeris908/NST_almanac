import urllib.request, ssl, re, json, sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

pages = [
   'page-66162180_50155777', 'page-66162180_50190588', 'page-66162180_50190660',
   'page-66162180_50651544', 'page-66162180_50736711', 'page-66162180_50736905',
   'page-66162180_50737105', 'page-66162180_50742426', 'page-66162180_51689599',
   'page-66162180_51689710', 'page-66162180_51689714', 'page-66162180_52396752',
   'page-66162180_52396753', 'page-66162180_52396755', 'page-66162180_52913184',
   'page-66162180_52913185', 'page-66162180_52913186', 'page-66162180_53570293',
   'page-66162180_53570318', 'page-66162180_53570373', 'page-66162180_53570375',
   'page-66162180_53570376'
]

class WikiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
    def handle_data(self, data):
        d = data.strip()
        if d: self.lines.append(d)

page_data = {}

for p in pages:
    url = f'https://vk.ru/{p}'
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, context=ctx).read().decode('windows-1251', errors='ignore')
        
        parser = WikiParser()
        parser.feed(html)
        
        # Find where wiki body starts
        # Usually has title or ТУРНИРНАЯ ТАБЛИЦА or 1 Тур
        text_lines = parser.lines
        
        # Find header/title
        header = ""
        for i, l in enumerate(text_lines[:40]):
            if any(k in l.lower() for k in ['сезон', 'лига', 'календарь', 'турнир']):
                header = l
                break
        
        # Check if contains match pairs
        has_scores = any(re.search(r'\d+:\d+', l) for l in text_lines)
        has_tours = any(re.search(r'\b\d+\s*Тур\b', l, re.I) for l in text_lines)
        
        page_data[p] = {
            'header': header,
            'lines_count': len(text_lines),
            'has_scores': has_scores,
            'has_tours': has_tours,
            'sample_lines': text_lines[25:60] if len(text_lines) > 25 else text_lines
        }
        print(f"{p}: Header='{header}' | scores={has_scores} | tours={has_tours} | lines={len(text_lines)}")
    except Exception as e:
        print(f"{p}: ERROR {e}")

with open('wiki_inspected.json', 'w', encoding='utf-8') as f:
    json.dump(page_data, f, ensure_ascii=False, indent=2)
