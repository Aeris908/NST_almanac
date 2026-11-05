"""Fetch the group's VK board topics and print their titles and comment counts."""

import json
import sys
import urllib.request

from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portal.env_file import secret  # noqa: E402

token = secret("VK_API_TOKEN")
if not token:
    sys.exit("Set VK_API_TOKEN in the environment or in .env before running this script (see .env.example).")
group_id = "66162180"

url = f"https://api.vk.ru/method/board.getTopics?group_id={group_id}&count=100&access_token={token}&v=5.199"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    resp = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    items = resp.get("response", {}).get("items", [])
    print(f"Total topics found: {len(items)}")
    for t in items:
        title = t.get("title", "")
        t_id = t.get("id")
        comments = t.get("comments", 0)
        print(f"  [ID: {t_id}] ({comments} comments) {title}")
except Exception as e:
    print("Error:", e)
