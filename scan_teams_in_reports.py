import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import re
import requests
from collections import defaultdict

TOKEN = "5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020"
GROUP_ID = 66162180

def get_topic_comments(tid):
    comments = []
    offset = 0
    while True:
        r = requests.get("https://api.vk.com/method/board.getComments", params={
            "group_id": GROUP_ID, "topic_id": tid, "offset": offset, "count": 100,
            "access_token": TOKEN, "v": "5.199"
        }).json()
        if "response" not in r: break
        items = r["response"]["items"]
        comments.extend(items)
        if len(items) < 100: break
        offset += 100
    return comments

TEAMS = ["бразилия", "италия", "германия", "аргентина", "камерун", "япония", "монголия", "сенегал", "мексика", "гвинея", "корея", "англия"]

for tid, name in [(54769667, "S9"), (52002075, "S8"), (49054760, "S7"), (39660451, "S6"), (36630593, "S5")]:
    comms = get_topic_comments(tid)
    print(f"\n=== {name} (Comments: {len(comms)}) ===")
    matches_with_teams = []
    for c in comms:
        txt = c.get("text", "")
        # check if contains digit score and any team
        if any(char.isdigit() for char in txt) and any(t in txt.lower() for t in TEAMS):
            lines = [l for l in txt.splitlines() if any(t in l.lower() for t in TEAMS) or (any(d in l for d in "0123456789") and (":" in l or "-" in l))]
            if lines:
                matches_with_teams.append(" // ".join(lines[:3]))
    print(f"Found {len(matches_with_teams)} reports with team mentions:")
    for m in matches_with_teams[:6]:
        print("  *", m[:120])
