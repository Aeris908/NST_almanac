"""Division Elo v2: дивизион задаёт исходный уровень, дальнейшие изменения — игры.

Базы 1800/1400/1000 и SCALE=400 — параметризация описанного владельцем разрыва уровней,
а не измеренные вероятности побед. Последующий переход не повышает рейтинг автоматически.
OT/PK уменьшает K. Простой учитывается отдельно от силы. Имена и титулы не дают очков.
"""
import math
import re
from datetime import datetime,timezone
from functools import lru_cache

from portal.names import clean_alias
from portal.roster_tables import SEASON_ROSTERS

MODEL_VERSION='division-elo-v2'
DIVISION_BASE={'Высшая':1800.0,'Средняя':1400.0,'Дворовая':1000.0}
R0=1400.0
SCALE=400.0
K_BY_WEIGHT={'league':24.0,'playoff':32.0,'other':16.0}
LEARNING_WINDOW=15
PROVISIONAL_K=1.0
MOV_CAP=1.25
RATING_FLOOR=0.0
FIRST_CALIBRATION_FORM_CAP=150.0
WIN_SCORE=1.0
OVERTIME_WIN_SCORE=1.0
DRAW_SCORE=.5
OVERTIME_LOSS_SCORE=0.0
LOSS_SCORE=0.0
SEASON_YEAR={'Season 1':2016.0,'Season 2':2016.4,'Season 3':2016.8,'Season 4':2017.5,
             'Season 5':2018.4,'Season 6':2019.0,'Season 7':2022.0,'Season 8':2024.0,'Season 9':2025.5}
SEASON_BOUNDS={1:(2015,2016),2:(2016,2016),3:(2016,2016),4:(2017,2018),5:(2018,2018),
               6:(2018,2019),7:(2020,2022),8:(2024,2024),9:(2025,2026)}


class EloError(ValueError):pass


def season_number(match):
    found=re.fullmatch(r'(?:Season|Сезон)\s+(\d+)',str(match.get('season') or ''))
    return int(found[1]) if found else None


def division(label):
    text=str(label or '').lower()
    if 'единая' in text or 'младшая' in text:return None
    for needle,tier in [('высш','Высшая'),('средн','Средняя'),('дворов','Дворовая')]:
        if needle in text:return tier
    return None


@lru_cache(maxsize=16)
def roster_divisions(number):
    result={}
    for label,names in SEASON_ROSTERS.get(str(number),{}).items():
        for player in names:
            if division(label):result.setdefault(clean_alias(player),set()).add(division(label))
    return result


def division_of(match,name):
    roster_tiers=roster_divisions(season_number(match)).get(name,set())
    # «Высшая» в неразобранных комментариях ранее использовалась как плейсхолдер.
    explicit=None if match.get('source')=='vk_comments_playoff' or match.get('is_playoff') or match.get('is_series') else division(match.get('league'))
    if explicit:return explicit
    return next(iter(roster_tiers)) if len(roster_tiers)==1 else None


def expected(rating,opponent):return 1.0/(1.0+10.0**((opponent-rating)/SCALE))


def actual_score(s1,s2,overtime=False,penalties=False):
    return (.5,.5) if s1==s2 else (1.0,0.0) if s1>s2 else (0.0,1.0)


def margin_multiplier(goal_difference):
    return min(1.0+.1*math.log1p(max(0,abs(int(goal_difference))-1)),MOV_CAP)


def weight_of(match):
    if match.get('is_playoff') or match.get('is_series'):return 'playoff'
    return 'league' if match.get('row_set') in ('pool','catalog',None) else 'other'


def k_factor(match,games_a,games_b,goal_difference):
    base=K_BY_WEIGHT[weight_of(match)]
    if match.get('ot') or match.get('pk'):return base*.75
    return base*(1 if match.get('is_series') else margin_multiplier(goal_difference))


def exact_year(match):
    value=str(match.get('played_on') or '')
    try:date=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:return None
    bounds=SEASON_BOUNDS.get(season_number(match))
    if bounds and not bounds[0]<=date.year<=bounds[1]:return None
    return date.year+(date.timetuple().tm_yday-1)/366.0


def rating_year(match):
    precise=exact_year(match)
    if precise is not None:return precise
    number=season_number(match)
    if number and 'Season '+str(number) in SEASON_YEAR:return SEASON_YEAR['Season '+str(number)]
    raw=str(match.get('source_date_raw') or '')
    if raw.isdigit() and len(raw)==10:return datetime.fromtimestamp(int(raw),timezone.utc).year
    for value in (match.get('doc_year'),match.get('tournament')):
        found=re.search(r'(19|20)\d{2}',str(value or ''))
        if found:return float(found[0])
    raise EloError('нет года партии')


def order_matches(matches):
    def key(match):
        number=season_number(match);year=rating_year(match)
        # Последовательность сезонов известна; чужая дата комментария не переносит S3 в S9.
        period=number
        if period is None:
            anchors=sorted((value,int(key.split()[-1])) for key,value in SEASON_YEAR.items())
            period=anchors[-1][1]+max(0,year-anchors[-1][0])
            if year<anchors[0][0]:period=0
            for (lo,a),(hi,b) in zip(anchors,anchors[1:]):
                if lo<=year<hi:period=a+(year-lo)/(hi-lo);break
        block=int(bool(match.get('is_playoff') or match.get('is_series')))
        return period,block,exact_year(match) or 9999,match.get('order_in_source') or 0,match.get('id') or 0
    return sorted(matches,key=key)


def play(match,rating,games,calibration=None):
    state=calibration if calibration is not None else {}
    players=[match['p1'],match['p2']];before=[]
    for name in players:
        tier=division_of(match,name)
        previous=state.setdefault(name,{'calibrated':False,'tier':None,'adjustment':0.0})
        value=rating.get(name,R0);adjustment=0.0
        if tier and not previous['calibrated']:
            residual=max(-FIRST_CALIBRATION_FORM_CAP,min(FIRST_CALIBRATION_FORM_CAP,value-R0))
            target=DIVISION_BASE[tier]+residual
            adjustment=target-value;value=target;previous['calibrated']=True
        if tier:previous['tier']=tier
        previous['adjustment']=round(adjustment,1)
        previous['pre_game_rating']=value
        before.append(value)
    if match.get('outcome_a') in ('win','loss') and match.get('outcome_b') in ('win','loss'):
        s1,s2=(1.,0.) if match['outcome_a']=='win' else (0.,1.)
    else:s1,s2=actual_score(match['s1'],match['s2'])
    k=k_factor(match,games.get(players[0],0),games.get(players[1],0),abs(match['s1']-match['s2']))
    r1,r2=before
    result=round(r1+k*(s1-expected(r1,r2)),1),round(r2+k*(s2-expected(r2,r1)),1)
    for name in players:games[name]=games.get(name,0)+1
    return result


def decay_penalty(years_inactive):return 0.0


def active_rating(rating,penalty=0):return round(rating,1)
