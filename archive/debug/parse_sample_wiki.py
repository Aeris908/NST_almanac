import urllib.request, ssl, sys, re
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = 'https://vk.ru/page-66162180_52396752'
req = urllib.request.Request(url, headers=headers)
html = urllib.request.urlopen(req, context=ctx).read().decode('windows-1251', errors='ignore')

# Extract title and body
from html.parser import HTMLParser
class CleanParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
    def handle_data(self, data):
        d = data.strip()
        if d: self.lines.append(d)

p = CleanParser()
p.feed(html)

print("Title / First lines:")
start_idx = 0
for i, l in enumerate(p.lines):
    if "ТУРНИРНАЯ ТАБЛИЦА" in l or "1 Тур" in l:
        start_idx = i
        break

print(f"Tournament content starts at line {start_idx}:")
for l in p.lines[start_idx:start_idx+100]:
    print(l)
