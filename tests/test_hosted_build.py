"""Публикация использует сохранённые решения редактора; локальный from-store не заменяется."""
from pathlib import Path
import subprocess
import pytest
import build_all

def calls(monkeypatch):
    result=[]
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setattr(build_all,'secret',lambda name:'configured')
    monkeypatch.setattr(build_all.subprocess,'run',lambda cmd,**kwargs:result.append((Path(cmd[1]).name,cmd[2:])))
    return result

def test_hosted_build_pulls_after_schema_and_before_page_generation(monkeypatch):
    seen=calls(monkeypatch);build_all.build_pages()
    names=[name for name,args in seen]
    assert names.index('import_live.py')<names.index('sync.py')<names.index('elo_review_queue.py')<names.index('build_master_table.py')
    assert next(args for name,args in seen if name=='sync.py')==['pull']

def test_from_store_and_local_build_do_not_replace_local_edits(monkeypatch):
    seen=calls(monkeypatch);build_all.build_pages(from_store=True)
    assert 'sync.py' not in [name for name,args in seen]
    seen.clear();monkeypatch.delenv('VERCEL');build_all.build_pages()
    assert 'sync.py' not in [name for name,args in seen]

def test_failed_server_snapshot_stops_before_publishing_stale_pages(monkeypatch):
    seen=calls(monkeypatch)
    def fail(cmd,**kwargs):
        name=Path(cmd[1]).name;seen.append((name,cmd[2:]))
        if name=='sync.py':raise subprocess.CalledProcessError(1,cmd)
    monkeypatch.setattr(build_all.subprocess,'run',fail)
    with pytest.raises(subprocess.CalledProcessError):build_all.build_pages()
    assert 'build_master_table.py' not in [name for name,args in seen]
