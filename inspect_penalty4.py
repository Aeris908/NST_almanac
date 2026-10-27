import urllib.request, re, sys

sys.stdout.reconfigure(encoding='utf-8')
url = "https://vk.com/topic-66162180_34920573"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=10).read().decode('cp1251', errors='ignore')
for m in re.finditer(r'challonge\.com[^\s<>"]+', html):
    print("Found Challonge:", m.group(0))
for m in re.finditer(r'vk\.cc[^\s<>"]+', html):
    print("Found vk.cc:", m.group(0))
for m in re.finditer(r'docs\.google\.com[^\s<>"]+', html):
    print("Found Google Docs:", m.group(0))
