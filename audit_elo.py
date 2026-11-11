"""Проверка охвата и устойчивости Elo без изменения базы и опубликованной формулы.

python audit_elo.py --output docs/elo-audit-2026-11-11
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from db import store
from db.pool import pool_from_db
from archive import elo_v1 as elo
from portal import master_table
from portal.build_soccer import compose_payload
from portal.master_tables import LEAGUE_TIERS,CURRENT_YEAR


def simulate(matches, mode='current'):
    ratings, games, peaks, last = {}, {}, {}, {}
    opponents, changes = defaultdict(list), defaultdict(list)
    squared_errors = []
    for match in elo.order_matches(matches):
        technical=master_table.technical_winner(match)
        if technical:
            last[technical]=elo.rating_year(match)
            continue
        a,b=match['p1'],match['p2']
        ra,rb=ratings.get(a,elo.R0),ratings.get(b,elo.R0)
        expected=elo.expected(ra,rb)
        actual=1.0 if match['s1']>match['s2'] else 0.0 if match['s1']<match['s2'] else .5
        squared_errors.append((expected-actual)**2)
        if mode=='current':
            na,nb=elo.play(match,ratings,games)
            k=elo.k_factor(match,games[a]-1,games[b]-1,abs(match['s1']-match['s2']))
        else:
            k=elo.K_BY_WEIGHT[elo.weight_of(match)]
            if mode=='no_boosts':
                s1,s2=elo.actual_score(match['s1'],match['s2'],match.get('ot'),match.get('pk'))
            else:
                s1,s2=actual,1-actual
                if match.get('ot') or match.get('pk'): k*=.75
            na,nb=round(ra+k*(s1-expected),1),round(rb+k*(s2-(1-expected)),1)
            games[a]=games.get(a,0)+1;games[b]=games.get(b,0)+1
        ratings[a],ratings[b]=na,nb
        for name in (a,b):
            peaks[name]=max(peaks.get(name,elo.R0),ratings[name]);last[name]=elo.rating_year(match)
        for name,opponent,old,new,score,other in [(a,b,ra,na,match['s1'],match['s2']),(b,a,rb,nb,match['s2'],match['s1'])]:
            opponents[name].append(opponent)
            changes[name].append({'match_id':match['id'],'season':match['season'],'stage':match.get('stage'),
                'opponent':opponent,'score':f'{score}:{other}','before':old,'after':new,'delta':round(new-old,1),
                'k':round(k,3),'win_lost_points':score>other and new<old,'loss_gained_points':score<other and new>old})
    return {'ratings':ratings,'games':games,'peaks':peaks,'last':last,'opponents':dict(opponents),'changes':dict(changes),
            'mse':sum(squared_errors)/len(squared_errors),'played':len(squared_errors)}


def audit(db_path=store.DB_PATH):
    matches=pool_from_db(db_path)
    profiles=compose_payload(db_path)['profiles']
    current=simulate(matches)
    variants={name:simulate(matches,name) for name in ('no_boosts','result_weight')}
    qualified=[]
    for name,rating in current['ratings'].items():
        profile=next(p for p in profiles if p['player']==name)
        played=current['games'][name];opponents=current['opponents'][name];changes=current['changes'][name]
        penalty=elo.decay_penalty(max(0,CURRENT_YEAR-current['last'][name]))
        rows={
            'player':name,'league':LEAGUE_TIERS.get(name,'?'),'display_league':'Высшая' if profile.get('is_hall_of_fame') else LEAGUE_TIERS.get(name,'Дворовая'),'elo':elo.active_rating(rating,penalty),
            'raw_elo':rating,'peak':current['peaks'][name],'rated_games':played,'career_matches':profile['matches'],
            'season_singles_records':sum(m.get('category') in ('season','cup') and not m.get('partner') for m in profile.get('match_history',[])),
            'distinct_opponents':len(set(opponents)),'provisional':played<elo.LEARNING_WINDOW,
            'decay':penalty,
            'same_tier_games':sum(LEAGUE_TIERS.get(other)==LEAGUE_TIERS.get(name) for other in opponents),
            'max_change':max(abs(row['delta']) for row in changes),
            'wins_losing_points':sum(row['win_lost_points'] for row in changes),
            'losses_gaining_points':sum(row['loss_gained_points'] for row in changes),
            'opponent_raw_average':round(sum(current['ratings'][other] for other in opponents)/len(opponents),1),
        }
        for variant,values in variants.items():
            rows[variant]=elo.active_rating(values['ratings'][name],rows['decay'])
        rows['flags']=[]
        if rows['provisional']:rows['flags'].append('предварительный рейтинг')
        if played<rows['season_singles_records']*.25:rows['flags'].append('пул меньше четверти сезонной истории; сверить единицы учёта')
        if rows['max_change']>=50:rows['flags'].append('изменение за игру >= 50')
        if rows['wins_losing_points']:rows['flags'].append('победы с потерей очков')
        if rows['losses_gaining_points']:rows['flags'].append('поражения с приростом очков')
        if rows['decay']>=100:rows['flags'].append('штраф за простой >= 100')
        if rows['display_league']!=rows['league']:rows['flags'].append('значок лиги отличается от классификации справочника')
        qualified.append(rows)
    qualified.sort(key=lambda p:-p['elo'])
    for rank,row in enumerate(qualified,1):row['rank']=rank
    for variant in variants:
        positions={row['player']:i for i,row in enumerate(sorted(qualified,key=lambda p:-p[variant]),1)}
        for row in qualified:row[variant+'_rank']=positions[row['player']]
    con=store.connect(db_path)
    try:
        seasons=dict(con.execute('select season,count(*) from v_rating_pool group by season'))
        technical=dict(con.execute('select status,count(*) from matches where in_rating_pool=1 group by status'))
        unresolved=[dict(zip(('id','a','b','s1','s2','phase','a_outcome','b_outcome'),r)) for r in con.execute(
            "select v.id,v.p1,v.p2,v.s1,v.s2,m.phase,a.outcome,b.outcome from v_rating_pool v "
            "join matches m on m.id=v.id join match_sides a on a.match_id=v.id and a.side_index=0 "
            "join match_sides b on b.match_id=v.id and b.side_index=1 where v.s1=v.s2 and v.pk=1")]
    finally:con.close()
    return {'pool_rows':len(matches),'rated_players':len(qualified),'profiles_total':len(profiles),
            'season_coverage':seasons,'statuses':technical,'players':qualified,
            'model_scores':{'current':current['mse'],**{key:value['mse'] for key,value in variants.items()}},
            'hanter_trace':current['changes'].get('Hanter',[]),'equal_goals_pk':unresolved}


def write_report(result,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with path.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        rows=[{**row,'flags':'; '.join(row['flags'])} for row in result['players']]
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# Аудит Elo: все рейтинговые игроки','',
           f"Пул: {result['pool_rows']} строк; {result['rated_players']} игроков с Elo из {result['profiles_total']} профилей.",
           'Это диагностика и расчёт альтернатив. Опубликованная формула и данные не изменялись.','',
           '## Обнаруженные проблемы и спорные свойства модели','',
           '- Предварительные рейтинги стоят в общем рейтинге без заметной маркировки.',
           '- Колонка матчей содержит карьеру всех форматов, а Elo — только явно включённый пул.',
           '- Множитель новичка повышает K обоим участникам. Вместе с поправкой счёта K доходит до 96.',
           '- Разница +1 даёт множитель 1,693; уже +2 достигает потолка 2. Разгромы почти не различаются.',
           '- При результате OT/PK 0,75 победитель может потерять очки против слабого соперника; проигравший — получить.',
           '- Старые сезоны представлены в пуле намного слабее новых. Формула не исправит отсутствующие матчи.',
           '- Простой вычитается из силы и меняет общий порядок легенд и действующих игроков.',
           '- Год рейтинга берётся из сезона раньше точной даты. Точка отсчёта простоя зафиксирована на 2025,5.',
           '- Статус легенды на витрине принудительно заменяет значок лиги на «Высшая», даже если классификация справочника другая. Это свойство представления, не подтверждение силы.',
           '', '## Охват по сезонам','', '| Сезон | Матчей в пуле |','|---|---:|']
    lines += [f'| {season} | {count} |' for season,count in result['season_coverage'].items()]
    lines += ['', '## Проверка всех игроков','',
              'Рейтинговые игры исключают технические победы. Сезонная история включает записи одиночных встреч регулярных сезонов и кубков; там могут быть сводки серий, поэтому число записей не равно числу отдельных рейтинговых игр. Карьера дополнительно включает другие форматы. Флаги — основания для проверки, а не доказательство неверного места игрока.','',
              '| Место | Игрок | Elo | Рейтинговых / сезонных записей / вся карьера | Соперников | Простой | Флаги |',
              '|---:|---|---:|---:|---:|---:|---|']
    lines += [f"| {p['rank']} | {p['player']} | {p['elo']} | {p['rated_games']} / {p['season_singles_records']} / {p['career_matches']} | {p['distinct_opponents']} | {p['decay']} | {'; '.join(p['flags']) or 'срабатываний нет'} |" for p in result['players']]
    lines += ['', '## Сравнение двух альтернатив на том же пуле','',
              'Вариант A: прежние очки 1 / 0,75 / 0,5, но без множителей новичка и счёта. Вариант B: те же базовые K, победа/ничья/поражение 1 / 0,5 / 0, а OT/PK уменьшает K на 25%. Штрафы простоя для сравнения оставлены прежними. Это не утверждённые новые модели.','',
              '| Игрок | Сейчас | A: без множителей | B: вес результата |','|---|---:|---:|---:|']
    lines += [f"| {p['player']} | {p['elo']} (#{p['rank']}) | {p['no_boosts']} (#{p['no_boosts_rank']}) | {p['result_weight']} (#{p['result_weight_rank']}) |" for p in result['players']]
    lines += ['', 'Средний квадрат разницы между ожиданием до игры и исходом по голам (победа 1, ничья 0,5, поражение 0; меньше — лучше). Это только диагностическая метрика на данном небольшом историческом пуле, без независимой тестовой выборки; она не доказывает справедливость мест между лигами:', '',json.dumps(result['model_scores'],ensure_ascii=False),'',
              '## Хантер: каждая рейтинговая игра','', '| Сезон | Соперник | Счёт | Было | Стало | Изменение | K |','|---|---|---|---:|---:|---:|---:|']
    lines += [f"| {r['season']} | {r['opponent']} | {r['score']} | {r['before']} | {r['after']} | {r['delta']} | {r['k']} |" for r in result['hanter_trace']]
    lines += ['', '## Следующий шаг','',
              'Сначала зафиксировать одинаковые правила включения матчей и восстановить сопоставимый охват сезонов. Сомнительные протоколы остаются в очереди лороведа. Затем выбрать формулу на одинаковом срезе и разделить подтверждённый рейтинг, калибровку и активность. Лиговые ярлыки и имена не используются для ручного назначения мест.','']
    path.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',default=str(store.DB_PATH));parser.add_argument('--output',type=Path,default=Path('docs/elo-audit-2026-11-11'));args=parser.parse_args()
    result=audit(args.db);write_report(result,args.output)
    print(json.dumps({'scores':result['model_scores'],'top':result['players'][:16]},ensure_ascii=False,indent=2))
