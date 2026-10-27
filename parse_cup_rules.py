import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
resp = requests.get("https://vk.com/page-66162180_53697368", headers=headers)
resp.encoding = "windows-1251"
soup = BeautifulSoup(resp.text, "html.parser")
body = soup.find(id="wk_content") or soup.find(class_="wk_text")
if body:
    print(body.get_text()[:4000])
