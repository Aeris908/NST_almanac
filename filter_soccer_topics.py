import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('all_group_topics.json', 'r', encoding='utf-8') as f:
    topics = json.load(f)

# Non-soccer blacklist
blacklist = [
    'nhl', 'tecmo', 'tmnt', 'sensible', 'issd', 'fats', 'contra', 'mario',
    'sonic', 'rally', 'bomber', 'excite', 'blades of steel', 'f1', 'ice climber',
    'killer instinct', 'eternal champions', 'nba', 'chip ’n dale', 'btdd', 'f1 race',
    'circus charlie', 'exerion', 'balloon fight', 'palamedes', 'street fighter',
    'micro machines', 'tiny toon', 'double dragon', 'battletoads', 'turtles',
    'shanghai', 'pool', 'tennis', 'baseball'
]

soccer_topics = []
for t in topics:
    title = t.get('title', '')
    tl = title.lower()
    if any(b in tl for b in blacklist):
        continue
    # check if related to tournaments
    if any(k in tl for k in ['soccer', 'goal', 'футбол', 'пенальти', 'кубок', 'межсезон', 'молодеж', 'молодёж', 'сольный', 'сезон', 'чемпионат', 'лиг', 'блиц', 'турнир']):
        soccer_topics.append(t)

print(f"Candidate soccer/tournament topics found: {len(soccer_topics)}")
for t in sorted(soccer_topics, key=lambda x: x.get('comments', 0), reverse=True):
    print(f"  [ID: {t['id']}] ({t.get('comments')} comments) {t['title']}")
