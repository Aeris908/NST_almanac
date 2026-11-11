"""Восстановление только явно подписанных командных протоколов из сохранённых источников.

python collectors/recover_team_archives.py
Не восстанавливает неизвестные составы, счёт по итоговой таблице или подписи из соседнего поста.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOPICS = {
    '31898219': 'III Командный Чемпионат (Летний 2015)',
    '35995200': 'V Командный Чемпионат по Goal 3',
}
EARLY_TITLE = 'I и II Командные Чемпионаты (Эпоха зарождения 2х2)'
# Только явно названные участники: варианты написания сохраняются в source_text.
NAMES = {
    'Huba_Buba_5': r'huba[ _-]*buba[ _-]*5|хуба',
    'eXponat': r'exponat', 'mafuta': r'mafuta|мафута', 'Jora': r'jora|жора',
    'TaRantull': r'tarantul+l?', 'Noboru': r'noboru', 'SideofClouds': r'sideofclouds',
    'MyNameIsFreeman': r'mynameisfreeman', 'BullDozeRrrr': r'bulldozer\w*|бульдозер',
    'Wolya63': r'wolya63', 'letopisec': r'letopisec|goodman', 'Partsigah': r'partsigah',
    'Alexasha': r'alexasha', 'Kinbeas': r'kinbeas', 'K-R': r'k-r',
    'teo_heel': r'teo_heel', 'ROC666': r'r[0o]c666', 'Angel': r'angel|ангел',
    'Davitel': r'davitel|давитель', 'Kunio': r'[kк]unio|кунио', 'Memori': r'memori|мемори',
    'esteban': r'esteban', 'Jgunishka': r'jgunishka|жгунишка', 'wenderfit': r'wenderfit',
    'Narak': r'narak', 'Lipetsk': r'lipetsk', 'edward54': r'edward(?:54)?',
    'PacnyTHuK': r'pacnythuk', 'Alpharushin': r'alpharushin', 'BZK': r'bzk',
    'BOP95': r'[bв]op95|вор95', 'Centurion': r'centurion|centzloy', 'Kotix': r'kotix',
    'Azatron': r'azatron', 'RVD (МГБ)': r'(?<![\w])rvd(?![\w])', 'Edexy': r'edexy',
    'LiptOn': r'lipton', 'Flash': r'flash', 'Tarantull': r'(?!)',
    'izzzotope': r'izzzotope', 'Буц': r'буц', 'Dopi': r'dopi',
    'FC Pushistik': r'(?:fc\s*)?pushistik', 'TEXAS': r'texas', 'starspro': r'starspro',
    'Aeris': r'aeris', 'Jamlight': r'jamlight', 'yoxter': r'yoxter',
    'Кирпич57': r'кирпич57', 'Rustin Cohle': r'rustin\s+cohle', 'Kubik': r'kubik',
    'ROOS': r'roos', 'Palka Palych': r'palka\s+palych', 'Ric25': r'ric25',
    'Focus': r'fo[ck]us', 'Romix': r'romix', 'Transistor': r'transistor',
    'Wanchous': r'wanch?ous', 'Telpecarne': r'telpecarne',
    'psycho': r'psycho', 'andrdjey': r'andrdjey', 'eXpress': r'express',
}
NAME_RE = re.compile('|'.join(f'(?P<n{i}>{pat})' for i, pat in enumerate(NAMES.values())), re.IGNORECASE)
NAME_KEYS = list(NAMES)
VS = re.compile(r'\bvs\.?\b|_vs_|\bпротив\b', re.IGNORECASE)
SCORE = re.compile(r'(\d{1,2})\s*(?:\(\s*(\d{1,2})\s*\))?\s*[:\-–]\s*(\d{1,2})(?:\s*\(\s*(\d{1,2})\s*\))?')


def names(text):
    found = [NAME_KEYS[int(m.lastgroup[1:])] for m in NAME_RE.finditer(text)]
    return found if len(found) == 2 and len(set(found)) == 2 else []


def pair(line):
    # Страны в скобках не часть состава; подписи игроков могут разделяться одним дефисом.
    bare = re.sub(r'\([^)]*\)', '', line)
    split = VS.split(bare, maxsplit=1)
    if len(split) != 2:
        split = re.split(r'\s+-\s+', bare, maxsplit=1)
    if len(split) != 2:
        return None
    a, b = names(split[0]), names(split[1])
    return (a, b) if a and b and not set(a) & set(b) else None


def score_of(line):
    m = SCORE.search(line)
    if not m:
        return None
    a, b = int(m[1]), int(m[3])
    pa, pb = m[2], m[4]
    if pa is None and a == b:
        tail = SCORE.search(line[m.end():])
        if tail: pa, pb = tail[1], tail[3]
    if (pa is None) != (pb is None):
        return None
    text = f'{a}:{b}'
    outcome = ['win', 'loss'] if a > b else ['loss', 'win'] if b > a else ['draw', 'draw']
    phase = 'regular'
    if pa is not None and a == b:
        if int(pa) == int(pb): return None
        text += f' (ПК {pa}:{pb})'
        outcome = ['win','loss'] if int(pa)>int(pb) else ['loss','win']
        phase = 'penalties'
    return [a, b], text, phase, outcome


def extract_post(post, tournament, origin, early=False):
    text = post['text']
    if re.search(r'\bQuote\b|Цитата|Результаты одной с половиной игры',text,re.IGNORECASE): return []
    current = None
    last_header = -100
    result = []
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    # Не выводим стадию из номера поста или соседнего отчёта.
    stage = '1/2 финала' if re.search(r'полуфинал|1[\\/]2\s*финал',text,re.IGNORECASE) else 'Финал' if re.search(r'(?:^|большой )финал(?:\s|,|$)',text,re.IGNORECASE|re.MULTILINE) else 'Стадия не указана'
    tour = re.search(r'(\d+)\s*[-йыие]*\s*тур',text,re.IGNORECASE)
    tour_label = f'{tour[1]} тур' if tour else 'Тур не указан'
    league = 'Высшая лига' if re.search('вышка|высшая',text,re.IGNORECASE) else 'Дворовая лига' if re.search('дворовая',text,re.IGNORECASE) else ''
    group = re.search(r'группа\s*([аaвb])',text,re.IGNORECASE)
    if group: league = 'Группа '+('А' if group[1].lower() in 'аa' else 'В')
    for i, line in enumerate(lines):
        p = pair(line)
        if p:
            current = p; last_header = i
        if not current or (early and i-last_header > 2): continue
        if re.search(r'итог|сч[её]т.*(?:очк|серии)|цитата|quote|http|\b20\d\d\b',line,re.IGNORECASE): continue
        # В VK отчёте заголовок со счётом обычно обозначает итог серии, а не голы игры.
        if p: continue
        parsed = score_of(line)
        if not parsed: continue
        # VK: принимаем только строки с названиями стран или нумерованную ногу.
        if not early and not re.search(r'англ|монг|браз|бра\b|кор|сен|мекс|тай|таил|гвин|гви\b|яп|гер|фрг|кам|ита|арг|^\d+[).]',line,re.IGNORECASE): continue
        scores, shown, phase, outcome = parsed
        result.append({'tournament':tournament,'league':league,'tour':tour_label,
                       'stage':(origin+' · ' if early else '')+stage,
                       'team_a':current[0],'team_b':current[1], 'score':scores,'score_text':shown,
                       'source_ref':f'team-recovered:{origin}:{post["id"]}:line-{i}',
                       'page_url':post['url'],'links':[], 'note':shown, 'phase':phase,
                       'outcome':outcome,'source_text':text,'source_page':origin})
    return result


def recover():
    cache = json.loads((ROOT/'vk_soccer_comments_cache.json').read_text(encoding='utf8'))
    games = []; report = {}
    for tid, title in TOPICS.items():
        subset=[]
        for p in cache[tid]:
            p={**p,'url':f'https://vk.com/topic-66162180_{tid}?post={p["id"]}'}
            subset += extract_post(p,title,'topic-'+tid)
        games += subset; report[tid]={'games':len(subset),'reports':len({x['page_url'] for x in subset})}
    for tid, label in [('27','I чемпионат 2012'),('85','II чемпионат 2013')]:
        posts=json.loads((ROOT/f'data/early_team_sources/forum-{tid}.json').read_text(encoding='utf8'))
        subset=[g for p in posts for g in extract_post(p,EARLY_TITLE,label,True)]
        games += subset; report[tid]={'games':len(subset),'reports':len({x['page_url'] for x in subset})}
    return games,report


def review_items(games):
    """Задача на исходный отчёт, а не отдельная задача на каждую его ногу."""
    cache = json.loads((ROOT/'vk_soccer_comments_cache.json').read_text(encoding='utf8'))
    sources = []
    for tid, title in TOPICS.items():
        sources += [(title, 'topic-'+tid, {**p, 'url':f'https://vk.com/topic-66162180_{tid}?post={p["id"]}'}) for p in cache[tid][1:]]
    for tid, label in [('27','I чемпионат 2012'),('85','II чемпионат 2013')]:
        posts=json.loads((ROOT/f'data/early_team_sources/forum-{tid}.json').read_text(encoding='utf8'))
        sources += [(EARLY_TITLE,label,p) for p in posts[1:]]
    by_url = {}
    for game in games: by_url.setdefault(game['page_url'], []).append(game)
    reviews = []
    for title, origin, post in sources:
        rows = by_url.get(post['url'], [])
        reasons = []
        if rows:
            if any('Стадия не указана' in r['stage'] for r in rows): reasons.append('стадия не доказана текстом отчёта')
            if any(r['tour']=='Тур не указан' for r in rows): reasons.append('не указан тур')
            if any(not r['league'] for r in rows): reasons.append('не доказана лига или группа')
            if any(n in {'Telpecarne','andrdjey','eXpress'} for r in rows for n in r['team_a']+r['team_b']): reasons.append('проверить личность и алиасы исторических ников')
        elif SCORE.search(post['text']) and re.search(r'vs|против|англ|монг|герман|кам-|яп-|\bita\b|\bcam\b',post['text'],re.IGNORECASE) and not re.search('завтра|по москве|icq|регламент',post['text'],re.IGNORECASE):
            reasons.append('протокол не разобран однозначно: проверить составы, ориентацию счёта, дубли цитат и статус игр')
        if not reasons: continue
        reviews.append({'source_ref':f'team-archive-review:{origin}:{post["id"]}',
                        'match_ref':rows[0]['source_ref'] if rows else None,
                        'задача':title+'. Проверить исходный отчёт и уточнить архив: '+ '; '.join(reasons)+'.',
                        'алгоритм_сомнение':'; '.join(reasons), 'ссылки':[post['url']],
                        'стороны':[' & '.join(rows[0]['team_a']),' & '.join(rows[0]['team_b'])] if rows else [],
                        'тур':rows[0]['tour'] if rows else '', 'как_выглядит':post['text']})
    reviews.append({'source_ref':'team-archive-review:team5-standings', 'match_ref':None,
                    'задача':'V командный: сверить призёров с источником. В описании золото Дворовой лиги указано у BOP95 & ROOS, а в сохранённой таблице на первом месте Focus & Romix. Таблица содержит неполное число встреч; не назначать чемпиона автоматически.',
                    'алгоритм_сомнение':'Итоговая подпись противоречит доступной таблице; проверить окончательность результатов.',
                    'ссылки':['https://docs.google.com/spreadsheets/d/1DkKAL4ZfHynXFv1VH9nF5WaiXB1Seli0ozRAjZELnew/edit#gid=0'],
                    'стороны':[], 'тур':'Итоги', 'как_выглядит':'В носителе BOP95 & ROOS названы чемпионами Дворовой лиги, в таблице лидирует Focus & Romix.'})
    reviews.append({'source_ref':'team-archive-review:early-bronze', 'match_ref':None,
                    'задача':'I командный: подтвердить итог матча за бронзу и полные составы призёров. Старое описание «Ветераны 2х2» доказательством не является.',
                    'алгоритм_сомнение':'Точный итог бронзовой серии не восстановлен; не назначать призёра по отдельной ноге.',
                    'ссылки':['https://technos-battles.ucoz.ru/forum/4-27-1'], 'стороны':[],
                    'тур':'Матч за 3-е место', 'как_выглядит':'В старой рамке вместо состава бронзовых призёров стояла подпись «Ветераны 2х2».'})
    return reviews


if __name__=='__main__':
    games,report=recover()
    (ROOT/'data/team_recovered_matches.json').write_text(json.dumps(games,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    (ROOT/'data/team_recovery_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    reviews=review_items(games)
    (ROOT/'data/team_recovery_review.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2)); print('Задач лороведу:',len(reviews))
