import urllib.request, ssl, re, sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
short_links = [
    'https://vk.cc/arue7I', 'https://vk.cc/arqdvQ', 'https://vk.cc/aptv2b',
    'https://vk.cc/arwohc', 'https://vk.cc/9cd4Eb', 'https://vk.cc/9ggBKi',
    'https://vk.cc/9io55j', 'https://vk.cc/9juChY'
]

for sl in short_links:
    try:
        req = urllib.request.Request(sl, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')
        # look for redirect link inside away.php
        m = re.search(r'href="(https?://[^"]+)"', html)
        if not m:
            m = re.search(r'location\.replace\("([^"]+)"\)', html)
        url = m.group(1) if m else "not found"
        print(f"{sl} => {url}")
    except Exception as e:
        print(f"{sl} => ERROR {e}")
