import urllib.request, re, sys
from urllib.parse import parse_qs, urlparse, unquote

sys.stdout.reconfigure(encoding='utf-8')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(NoRedirect)
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = sys.argv[1:] if len(sys.argv) > 1 else [
    "https://vk.cc/cZ3epP",
    "https://vk.cc/cZ3eyu",
    "https://vk.cc/cZ3eBk"
]

for short in urls:
    req = urllib.request.Request(short, headers=headers)
    try:
        resp = opener.open(req)
        print(f"{short} -> 200: {resp.geturl()}")
    except urllib.error.HTTPError as e:
        if e.code in (301, 302):
            loc = e.headers.get('Location', '')
            parsed = urlparse(loc)
            qs = parse_qs(parsed.query)
            target = qs.get('to', [''])[0]
            print(f"{short} -> {e.code}: {unquote(target) if target else loc}")
        else:
            print(f"{short} -> {e.code}")
