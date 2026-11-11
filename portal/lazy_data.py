"""Статические части данных с адресами по содержимому; расчёты API остаются полными."""
import copy
import hashlib
import json
from pathlib import Path


def chunk(value, directory):
    encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    name = hashlib.sha256(encoded).hexdigest()[:20] + '.json'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(encoded)
    return 'site-data/' + name


def soccer_summary(payload, directory):
    """Полный payload не мутируется: предпросмотр и статистика используют все протоколы."""
    result = copy.deepcopy(payload)
    def profiles(value):
        if isinstance(value, dict):
            if 'match_history' in value:
                value['lazy_url'] = chunk({'match_history':value.pop('match_history')}, directory)
            for child in list(value.values()):
                profiles(child)
        elif isinstance(value, list):
            for child in value:
                profiles(child)
    profiles(result)
    for key in ('seasons','team_tournaments','special_tournaments'):
        for item in result.get(key, []):
            for field in ('matches','playoff_matches'):
                if isinstance(item.get(field),list):item[field]=[copy.deepcopy(game) for game in item[field]]
                counts={}
                for game in item.get(field,[]) or []:
                    if not isinstance(game,dict):continue
                    identity={k:game.get(k) for k in ('p1','p2','t1','t2','tour','league','stage','vk_url','source_ref')}
                    token=hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:12]
                    counts[token]=counts.get(token,0)+1
                    game['_anchor']=token+'-'+str(counts[token])
            url = chunk(item, directory)
            header = {k:v for k,v in item.items() if k in ('id','name','title','year','season_year','champion','participants_count')}
            item.clear()
            item.update(header, lazy_url=url)
    return result


def catalog_summary(payload):
    result = copy.deepcopy(payload)
    for player in result.get('players', []):
        # Каталог использует только пять последних исходов; подробная история доступна в дисциплине.
        player['matches'] = [{'res_type':m.get('res_type')} for m in player.get('matches', [])[:5]]
    return result
