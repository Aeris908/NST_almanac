import urllib.request, ssl, sys, re
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()
req = urllib.request.Request('https://away.vk.ru/away.php?rh=af3d146e-6330-4b92-b960-4f538cf16f83', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req, context=ctx).read().decode('windows-1251', errors='ignore')

# Search for any href or URL
for m in re.finditer(r'(docs\.google\.com[^\s"\'<>]+|challonge\.com[^\s"\'<>]+|vk\.com/page[^\s"\'<>]+|vk\.ru/page[^\s"\'<>]+)', html):
    print("Found destination:", m.group(1))

# Also search for 'cc/' resolution or any link inside page
links = re.findall(r'<a[^>]+href="([^"]+)"', html)
for l in links:
    if not 'vk.' in l:
        print("Link:", l)
