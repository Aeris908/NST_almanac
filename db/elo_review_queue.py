"""Сомнительные даты рейтинговой истории — в очередь лороведу, без догадки о правильной дате."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from db import store
from db.rating_history import rating_history
from db.review_queue import upsert,remove_obsolete

BATCH='elo_review'


def refresh(db_path=store.DB_PATH):
    _,info=rating_history(db_path)
    con=store.connect(db_path)
    try:
        seen=set()
        for item in info['reviews']:
            mid=item['id'];ref='rating-date:'+str(item['source_ref'] or mid);seen.add((BATCH,ref))
            links=[r[0] for r in con.execute('select url from match_links where match_id=?',(mid,))]
            payload={'задача':f"{item['season']}: {item['p1']} — {item['p2']}. Проверить дату рейтинговой игры.",
                     'алгоритм_сомнение':item['reason'],'стороны':[item['p1'],item['p2']],
                     'как_выглядит':'В базе стоит дата '+item['played_on']+'. До проверки порядок определяется сезоном и источником.',
                     'ссылки':links,'source_ref':item['source_ref']}
            upsert(con,BATCH,'rating_audit',ref,payload,'conflict',mid)
        remove_obsolete(con,[BATCH],seen);con.commit();return len(seen)
    finally:con.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--db',default=str(store.DB_PATH));args=parser.parse_args()
    print('Задач по датам рейтинга:',refresh(args.db))
