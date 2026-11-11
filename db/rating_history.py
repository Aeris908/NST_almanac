"""Elo v2: единая сезонная история 1×1, без дублей, технических игр и повторного счёта серии."""
import re
import sqlite3
from collections import Counter

from db import store
from portal.names import clean_alias


SQL = """
select v.*,m.league,m.tour,m.phase,m.hidden_by,m.in_rating_pool,m.status,
       a.outcome as outcome_a,b.outcome as outcome_b
from v_singles_pool v
join matches m on m.id=v.id
join tournaments t on t.id=m.tournament_id
join disciplines d on d.id=t.discipline_id
join match_sides a on a.match_id=m.id and a.side_index=0
join match_sides b on b.match_id=m.id and b.side_index=1
where d.slug='soccer' and m.hidden_by is null
  and (m.row_set in ('catalog','pool') or m.in_rating_pool=1)
order by m.order_in_source,m.id
"""


def rating_history(db_path=store.DB_PATH):
    con=store.connect(db_path);con.row_factory=sqlite3.Row
    try:
        rows=[dict(row) for row in con.execute(SQL)]
        opt_out={r[0] for r in con.execute("select distinct m.id from matches m join corrections c "
            "on c.table_name='matches' and c.row_id=m.id where m.in_rating_pool=0 "
            "and c.field='in_rating_pool' and c.new_value='0' and c.reverted_at is null")}
    finally:con.close()
    # Проверенная сводка и ноги той же кубковой встречи не являются независимыми результатами.
    def meeting(row):return row['season'],tuple(sorted([clean_alias(row['p1']),clean_alias(row['p2'])]))
    summaries={meeting(row) for row in rows if row['source']=='cup_tables'}
    included=[];excluded=[];reviews=[]
    for row in rows:
        reason=None
        seasonal=bool(re.fullmatch(r'(?:Season|Сезон)\s+[1-9]',str(row['season'])))
        if not seasonal and not row['in_rating_pool']:continue
        if row['row_set']=='catalog' and row['source']=='sportcup_api' and row['season'] in ('Season 8','Season 9'):
            # from_sportcup_api — документированная проекция того же пула. Не зависит от
            # состояния close_sportcup_pairs и количества исключённых технических строк.
            reason='витринная проекция уже учтённого пула Sportcup'
        elif row['id'] in opt_out:reason='явное исключение редактором'
        elif row['status']!='played' or row['is_technical']:reason='технический или несыгранный результат'
        elif row['s1'] is None or row['s2'] is None:reason='счёт не подтверждён'
        elif row['source']!='cup_tables' and meeting(row) in summaries and (
                row['is_playoff'] or any(word in ' '.join(str(row.get(k) or '') for k in ('tour','league','stage')).lower() for word in ('плей-офф','кубок','финал'))):
            reason='отдельная нога серии с уже учтённой сводкой'
        elif row['s1']==row['s2'] and row['phase'] in ('penalties','overtime_penalties','overtime') and {row['outcome_a'],row['outcome_b']}!={'win','loss'}:
            reason='не подтверждён победитель дополнительного времени / буллитов'
        elif row['outcome_a'] not in ('win','loss','draw') or row['outcome_b'] not in ('win','loss','draw'):
            reason='исход не является сыгранным результатом'
        if reason:
            excluded.append({'id':row['id'],'season':row['season'],'p1':row['p1'],'p2':row['p2'],'reason':reason});continue
        row['ot']=row['phase'] in ('overtime','overtime_penalties')
        row['pk']=row['phase'] in ('penalties','overtime_penalties')
        row['is_series']=row['source']=='cup_tables'
        row['is_forfeit']=False
        included.append(row)
        from portal import elo
        played=str(row.get('played_on') or '')
        bounds=elo.SEASON_BOUNDS.get(elo.season_number(row))
        if played and bounds and played[:4].isdigit() and not bounds[0]<=int(played[:4])<=bounds[1]:
            reviews.append({'id':row['id'],'source_ref':row.get('source_ref'),'season':row['season'],'p1':row['p1'],'p2':row['p2'],
                            'played_on':played,'reason':'Дата записи противоречит периоду сезона. Проверить дату самой игры и дату публикации источника.'})
    return included,{'model':'division-elo-v2','included':len(included),'seasons':dict(Counter(row['season'] for row in included)),
                     'excluded':excluded,'reviews':reviews,'excluded_reasons':dict(Counter(row['reason'] for row in excluded))}


def rating_history_from_db(db_path=store.DB_PATH):
    return rating_history(db_path)[0]
