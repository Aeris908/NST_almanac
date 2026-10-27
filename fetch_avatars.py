import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

TOKEN = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'

player_to_vk = {
    'Aeris': 689482217,
    'ectoPower': 22217971,
    'Kunio': 94258064,
    'PacnyTHuK': 112974978,
    'Romix': 40491805,
    'Ric25': 333783566,
    'Memori': 286855730,
    'leonudomlya': 143684,
    'Rock': 859818719,
    'Буц': 203194115,
    'Kubik': 63552804,
    'Yuliy_Cezar': 106241917,
    'Dune': 4532629,
    'Jamlight': 177971007,
    'yoxter': 693390,
    'frzz': 178878295,
    'Sokol': 753577095,
    'Hanter': 444200773,
    'Taeda': 24192052,
    'Ryumaru': 284967568,
    'ruby': 170637841,
    'Cyneprepou4uk': 234423097,
}

uids_str = ','.join(str(v) for v in player_to_vk.values())
resp = requests.get('https://api.vk.com/method/users.get', params={
    'user_ids': uids_str,
    'fields': 'photo_200,domain,first_name,last_name',
    'access_token': TOKEN,
    'v': '5.199'
}, timeout=10).json()

users = {u['id']: u for u in resp.get('response', [])}
avatars = {}
for p, uid in player_to_vk.items():
    u = users.get(uid, {})
    name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
    photo = u.get('photo_200', '')
    print(f"{p:<14} -> VK: {uid:<10} | {name:<22} | {photo[:45]}...")
    avatars[p] = {
        'vk_id': uid,
        'vk_name': name,
        'avatar_url': photo,
        'domain': u.get('domain', '')
    }

with open('player_avatars.json', 'w', encoding='utf-8') as f:
    json.dump(avatars, f, ensure_ascii=False, indent=2)

print(f"Successfully saved {len(avatars)} player avatars to player_avatars.json!")
